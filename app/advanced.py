"""Copy-only native format recovery in a bounded child process.

This module does not repair files in place. A readable result is not proof that
all original content survived. The report records omissions and format changes.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile

from localdesk.safety import InputError, MAX_FILE_BYTES, open_zip, safe_xml

NATIVE = {"pdf", "jpeg", "gif", "sqlite", "video", "jsonl", "gzip"}


def native_kind(raw: bytes, name: str, detected: str) -> str:
    extension = Path(name).suffix.lower()
    if extension in {".jsonl", ".ndjson"}:
        return "jsonl"
    if (len(raw) >= 12 and raw[4:8] == b"ftyp") or raw.startswith(b"\x1aE\xdf\xa3"):
        return "video"
    return detected


def request(raw: bytes, name: str, *, recover=False) -> dict:
    if len(raw) > MAX_FILE_BYTES:
        raise InputError("The source exceeds 25 MiB.")
    envelope = {
        "raw": base64.b64encode(raw).decode("ascii"),
        "name": name,
        "recover": recover,
    }
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.recovery_worker"],
            input=json.dumps(envelope),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=60,
            cwd=Path(__file__).resolve().parents[1],
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise InputError(
            "Recovery reached its 60 second limit. Use a smaller file."
        ) from exc
    if result.returncode or len(result.stdout) > 38_000_000:
        raise InputError("The recovery worker stopped without a valid result.")
    try:
        response = json.loads(result.stdout)
    except ValueError as exc:
        raise InputError("The recovery worker returned invalid data.") from exc
    if response.get("error"):
        raise InputError(response["error"])
    if "content" in response:
        response["content"] = base64.b64decode(response["content"], validate=True)
    return response


def process(raw: bytes, name: str, recover=False) -> dict:
    from .formats import identify

    kind = native_kind(raw, name, identify(raw, name)["kind"])
    notes, details, data, extension = [], {}, b"", ""
    if kind == "pdf":
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(io.BytesIO(raw), strict=False)
        if reader.is_encrypted:
            raise InputError("Unlock this PDF in its normal application first.")
        if not 1 <= len(reader.pages) <= 100:
            raise InputError("Recover PDFs with 1 to 100 pages per batch.")
        details["readable_pages"] = len(reader.pages)
        if recover:
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            result = io.BytesIO()
            writer.write(result)
            data = result.getvalue()
            if (
                len(PdfReader(io.BytesIO(data), strict=True).pages)
                != details["readable_pages"]
            ):
                raise InputError("The rebuilt PDF failed page-count verification.")
            extension = ".pdf"
        notes.append(
            "Rebuilt readable PDF page objects. Open the copy to check layout and missing content."
        )
        notes.append(
            "Recovery is not sanitization. Original page resources can contain active or sensitive data."
        )
    elif kind in {"jpeg", "gif"}:
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(raw)) as original:
            if original.width * original.height > 20_000_000:
                raise InputError("The image exceeds 20 million pixels.")
            details.update(
                width=original.width,
                height=original.height,
                frames=getattr(original, "n_frames", 1),
            )
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.load()
            if recover:
                result = io.BytesIO()
                image.save(result, format="PNG")
                data = result.getvalue()
                with Image.open(io.BytesIO(data)) as verify:
                    verify.verify()
                extension = ".png"
            image.close()
        notes.append(
            "Decoded surviving image data into a new PNG without source metadata."
        )
        if details["frames"] > 1:
            notes.append(
                "Only the first frame was exported. Other animation frames were not recovered."
            )
    elif kind == "jsonl":
        from localdesk.parsers import decode_text

        text, _ = decode_text(raw)
        records, excluded = [], []
        lines = text.splitlines()
        if len(lines) > 50000:
            raise InputError("JSONL exceeds 50,000 lines.")
        for number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                excluded.append(number)
        if not records:
            raise InputError("No valid JSONL records survived.")
        details.update(valid_records=len(records), excluded_lines=excluded)
        if recover:
            data = (
                "\n".join(json.dumps(row, ensure_ascii=False) for row in records) + "\n"
            ).encode("utf-8")
            extension = ".jsonl"
        notes.append(
            f"Recovered {len(records)} complete JSON records. Excluded {len(excluded)} invalid lines."
        )
        if excluded:
            notes.append(
                "Excluded line numbers: " + ", ".join(map(str, excluded[:100]))
            )
    elif kind == "gzip":
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as source:
            decoded = source.read(MAX_FILE_BYTES + 1)
        if len(decoded) > MAX_FILE_BYTES:
            raise InputError("Expanded gzip data exceeds 25 MiB.")
        details["expanded_bytes"] = len(decoded)
        if recover:
            data, extension = decoded, ".bin"
        notes.append(
            "Decompressed data and verified the gzip trailer. The generic extension does not identify its contents."
        )
    elif kind == "sqlite":
        with tempfile.TemporaryDirectory(prefix="recoverylab-sqlite-") as temp:
            source_path, target_path = (
                Path(temp) / "input.sqlite3",
                Path(temp) / "output.sqlite3",
            )
            source_path.write_bytes(raw)
            from urllib.parse import quote

            connection = sqlite3.connect(
                "file:" + quote(source_path.as_posix()) + "?mode=ro", uri=True
            )
            try:
                connection.execute("PRAGMA trusted_schema=OFF")
                connection.execute("PRAGMA query_only=ON")
                tables = connection.execute(
                    "SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
                if len(tables) > 500:
                    raise InputError("This database exceeds 500 tables.")
                try:
                    details["integrity"] = connection.execute(
                        "PRAGMA quick_check"
                    ).fetchone()[0]
                except sqlite3.DatabaseError:
                    details["integrity"] = "Integrity check could not complete."
                details["tables"] = [row[0] for row in tables]
                if recover:
                    destination = sqlite3.connect(target_path)
                    try:
                        if details["integrity"] == "ok":
                            connection.backup(destination)
                            notes.append(
                                "Copied the readable database and retained its schema. The integrity check passed."
                            )
                        else:
                            recovered, omitted = 0, []
                            for table, sql in tables:
                                if not sql or "VIRTUAL TABLE" in sql.upper():
                                    omitted.append(table)
                                    continue
                                quoted = '"' + table.replace('"', '""') + '"'
                                try:
                                    cursor = connection.execute(
                                        "SELECT * FROM " + quoted
                                    )
                                    columns = [d[0] for d in cursor.description]
                                    rows = cursor.fetchmany(100001)
                                    if len(rows) > 100000:
                                        raise sqlite3.DatabaseError("Row bound reached")
                                    ddl = ",".join(
                                        '"' + c.replace('"', '""') + '" BLOB'
                                        for c in columns
                                    )
                                    destination.execute(
                                        "CREATE TABLE " + quoted + "(" + ddl + ")"
                                    )
                                    destination.executemany(
                                        "INSERT INTO "
                                        + quoted
                                        + " VALUES("
                                        + ",".join("?" for _ in columns)
                                        + ")",
                                        rows,
                                    )
                                    recovered += len(rows)
                                except sqlite3.DatabaseError:
                                    omitted.append(table)
                            if not recovered:
                                raise InputError(
                                    "No complete table rows could be recovered."
                                )
                            notes.extend(
                                [
                                    f"Recovered {recovered} readable rows into simple tables.",
                                    "Original indexes, constraints, views, and triggers were not reconstructed.",
                                    "Omitted tables: " + ", ".join(omitted),
                                ]
                            )
                        destination.commit()
                        if (
                            destination.execute("PRAGMA integrity_check").fetchone()[0]
                            != "ok"
                        ):
                            raise InputError(
                                "The recovered database failed integrity checks."
                            )
                    finally:
                        destination.close()
                    data, extension = target_path.read_bytes(), ".sqlite3"
            finally:
                connection.close()
    elif kind == "video":
        ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
        if not ffmpeg or not ffprobe:
            raise InputError(
                "Install local FFmpeg and ffprobe to inspect or remux video."
            )
        with tempfile.TemporaryDirectory(prefix="recoverylab-media-") as temp:
            source, output = Path(temp) / "source.media", Path(temp) / "recovered.mkv"
            source.write_bytes(raw)
            probe = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-show_streams",
                    "-of",
                    "json",
                    str(source),
                ],
                capture_output=True,
                timeout=15,
                check=False,
            )
            if probe.returncode:
                raise InputError(
                    "No readable media streams were found. Missing container headers may need a reference recording."
                )
            streams = json.loads(probe.stdout).get("streams", [])
            details["streams"] = [
                {"type": s.get("codec_type"), "codec": s.get("codec_name")}
                for s in streams
            ]
            if not any(s.get("codec_type") in {"audio", "video"} for s in streams):
                raise InputError("No readable audio or video stream exists.")
            if recover:
                result = subprocess.run(
                    [
                        ffmpeg,
                        "-nostdin",
                        "-v",
                        "error",
                        "-protocol_whitelist",
                        "file,pipe",
                        "-fflags",
                        "+genpts",
                        "-i",
                        str(source),
                        "-map",
                        "0:v?",
                        "-map",
                        "0:a?",
                        "-c",
                        "copy",
                        "-n",
                        str(output),
                    ],
                    capture_output=True,
                    timeout=40,
                    check=False,
                )
                if result.returncode or not output.is_file():
                    raise InputError(
                        "FFmpeg could not remux the surviving streams without transcoding."
                    )
                verify = subprocess.run(
                    [
                        ffprobe,
                        "-v",
                        "error",
                        "-protocol_whitelist",
                        "file,pipe",
                        "-show_streams",
                        "-of",
                        "json",
                        str(output),
                    ],
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
                if verify.returncode or not json.loads(verify.stdout).get("streams"):
                    raise InputError("The remuxed copy failed stream verification.")
                data, extension = output.read_bytes(), ".mkv"
            notes.append(
                "Remuxed readable audio and video streams. Missing packets were not recreated. Subtitles and attachments were omitted."
            )
    else:
        raise InputError("No native recovery method exists for this format.")
    if len(data) > MAX_FILE_BYTES:
        raise InputError("The recovered output exceeds 25 MiB.")
    return {
        "kind": kind,
        "details": details,
        "notes": notes,
        "extension": extension,
        **({"content": base64.b64encode(data).decode("ascii")} if recover else {}),
    }


def office_copy(raw: bytes, kind: str):
    """Retain an Office extension only when required package parts survive."""
    from .formats import zip_contents

    entries, notes, _ = zip_contents(raw)
    main = {
        "docx": "word/document.xml",
        "xlsx": "xl/workbook.xml",
        "pptx": "ppt/presentation.xml",
    }[kind]
    required = {"[Content_Types].xml", "_rels/.rels", main}
    valid = required.issubset(entries)
    if valid:
        try:
            for name, content in entries.items():
                if name.endswith((".xml", ".rels")):
                    safe_xml(content)
        except Exception:
            valid = False
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, content in entries.items():
            target.writestr(name, content)
    notes.append(
        "Recovered package structure. Open the result in its normal application to verify layout and completeness."
    )
    if not valid:
        notes.append(
            "Required Office XML parts were missing or invalid. Exported surviving parts as ZIP instead."
        )
    return stream.getvalue(), "." + kind if valid else ".zip", notes
