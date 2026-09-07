"""File identification and conservative, inspectable repair operations.

A repair can only use bytes that still exist. Missing content is never invented.
All outputs are new files. Recovery status is evidence-based, not a probability.
"""

from __future__ import annotations
import csv
import hashlib
import io
import json
import math
import re
import struct
import zipfile
import zlib
from collections import Counter
from pathlib import Path
from localdesk.parsers import decode_text
from localdesk.safety import (
    InputError,
    MAX_ARCHIVE_BYTES,
    MAX_ARCHIVE_ENTRIES,
    MAX_FILE_BYTES,
    archive_name_ok,
    open_zip,
    safe_xml,
)


def identify(raw: bytes, name: str = "") -> dict:
    signatures = [
        (b"%PDF-", "pdf", ".pdf"),
        (b"\x89PNG\r\n\x1a\n", "png", ".png"),
        (b"\xff\xd8\xff", "jpeg", ".jpg"),
        (b"PK\x03\x04", "zip", ".zip"),
        (b"PK\x05\x06", "zip", ".zip"),
        (b"\x1f\x8b", "gzip", ".gz"),
        (b"SQLite format 3\x00", "sqlite", ".sqlite3"),
        (b"GIF87a", "gif", ".gif"),
        (b"GIF89a", "gif", ".gif"),
    ]
    for signature, kind, ext in signatures:
        if raw.startswith(signature):
            if kind == "zip":
                try:
                    with open_zip(raw) as archive:
                        names = set(archive.namelist())
                        for required, office in [
                            ("word/document.xml", "docx"),
                            ("xl/workbook.xml", "xlsx"),
                            ("ppt/presentation.xml", "pptx"),
                        ]:
                            if required in names:
                                return {
                                    "kind": office,
                                    "extension": "." + office,
                                    "basis": "ZIP signature and Office parts",
                                }
                except (zipfile.BadZipFile, InputError):
                    pass
            return {"kind": kind, "extension": ext, "basis": "File signature"}
    extension = Path(name).suffix.lower()
    if extension in {".json", ".csv", ".tsv", ".txt", ".md", ".xml"}:
        return {
            "kind": extension[1:],
            "extension": extension,
            "basis": "File extension, checked during inspection",
        }
    try:
        text, _ = decode_text(raw)
        if text.lstrip().startswith(("{", "[")):
            return {"kind": "json", "extension": ".json", "basis": "Text structure"}
        if (
            "\x00" not in text
            and text.strip()
            and sum(c.isprintable() or c.isspace() for c in text) / len(text) > 0.95
        ):
            return {"kind": "txt", "extension": ".txt", "basis": "Readable text bytes"}
    except (UnicodeError, InputError):
        pass
    return {"kind": "unknown", "extension": "", "basis": "No supported signature"}


def trailing_comma_fix(text: str) -> tuple[str, int]:
    output, quoted, escaped, removed = [], False, False, 0
    for index, char in enumerate(text):
        if quoted:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
            output.append(char)
        elif char == ",":
            next_index = index + 1
            while next_index < len(text) and text[next_index].isspace():
                next_index += 1
            if next_index < len(text) and text[next_index] in "}]":
                removed += 1
            else:
                output.append(char)
        else:
            output.append(char)
    return "".join(output), removed


def read_csv(text: str) -> tuple[list[list[str]], str]:
    sample = text[:16_384]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        counts = {c: sample.count(c) for c in ",;\t|"}
        delimiter = max(counts, key=counts.get) if any(counts.values()) else ","
    rows = []
    for row in csv.reader(
        io.StringIO(text, newline=""), delimiter=delimiter, strict=True
    ):
        if len(row) > 200 or len(rows) >= 50_000:
            raise InputError("CSV input exceeds 200 columns or 50,000 rows.")
        rows.append(row)
    return rows, delimiter


def png_chunks(raw: bytes) -> list[dict]:
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise InputError("The PNG signature is missing.")
    position, chunks = 8, []
    while position + 12 <= len(raw):
        size = struct.unpack(">I", raw[position : position + 4])[0]
        end = position + 12 + size
        if size > MAX_FILE_BYTES or end > len(raw):
            raise InputError("A PNG chunk is truncated.")
        kind = raw[position + 4 : position + 8]
        payload = raw[position + 8 : position + 8 + size]
        expected = struct.unpack(">I", raw[position + 8 + size : end])[0]
        actual = zlib.crc32(kind + payload) & 0xFFFFFFFF
        chunks.append(
            {
                "type": kind.decode("ascii", errors="replace"),
                "length": size,
                "crc_ok": expected == actual,
                "start": position,
                "end": end,
            }
        )
        position = end
        if kind == b"IEND":
            break
    if not chunks or chunks[0]["type"] != "IHDR" or chunks[0]["length"] != 13:
        raise InputError("The PNG header chunk is missing or invalid.")
    if not any(c["type"] == "IDAT" for c in chunks):
        raise InputError("The PNG has no image-data chunk.")
    if chunks[-1]["type"] != "IEND":
        raise InputError("The PNG end chunk is missing.")
    return chunks


def salvage_zip(raw: bytes) -> tuple[dict[str, bytes], list[str]]:
    """Recover CRC-verified local ZIP entries when the central directory is lost."""
    output, notes, position, total = {}, [], 0, 0
    while position < len(raw) and len(output) < MAX_ARCHIVE_ENTRIES:
        start = raw.find(b"PK\x03\x04", position)
        if start < 0 or start + 30 > len(raw):
            break
        fields = struct.unpack("<IHHHHHIIIHH", raw[start : start + 30])
        _, _, flags, method, _, _, crc, compressed_size, size, name_len, extra_len = (
            fields
        )
        data_start = start + 30 + name_len + extra_len
        position = max(start + 4, data_start)
        if data_start > len(raw):
            notes.append("Skipped a truncated local header.")
            continue
        try:
            name = raw[start + 30 : start + 30 + name_len].decode(
                "utf-8" if flags & 0x800 else "cp437"
            )
        except UnicodeDecodeError:
            notes.append("Skipped an invalid entry name.")
            continue
        if not archive_name_ok(name) or flags & 1 or name in output:
            notes.append(f"Skipped unsafe, encrypted, or repeated entry: {name[:120]}")
            continue
        if name.endswith("/"):
            continue
        if method not in {0, 8} or size > MAX_FILE_BYTES:
            notes.append(f"Skipped unsupported entry: {name[:120]}")
            continue
        try:
            if method == 0:
                if flags & 8:
                    raise ValueError(
                        "Stored entries with unknown sizes cannot be recovered safely."
                    )
                end = data_start + compressed_size
                if end > len(raw):
                    raise ValueError("Entry data is missing.")
                content = raw[data_start:end]
            else:
                decompressor = zlib.decompressobj(-15)
                content = decompressor.decompress(raw[data_start:], MAX_FILE_BYTES + 1)
                if len(content) > MAX_FILE_BYTES or not decompressor.eof:
                    raise ValueError("Entry is too large or incomplete.")
                consumed = len(raw) - data_start - len(decompressor.unused_data)
                end = data_start + consumed
                if flags & 8:
                    descriptor = end + (4 if raw[end : end + 4] == b"PK\x07\x08" else 0)
                    if descriptor + 12 > len(raw):
                        raise ValueError("The data descriptor is missing.")
                    crc, compressed_size, size = struct.unpack(
                        "<III", raw[descriptor : descriptor + 12]
                    )
                    end = descriptor + 12
                if consumed > MAX_FILE_BYTES:
                    raise ValueError("Compressed entry is too large.")
            if len(content) != size or (zlib.crc32(content) & 0xFFFFFFFF) != crc:
                raise ValueError("Entry failed its size or CRC check.")
            if (
                len(content) > 1_000_000
                and len(content) / max(compressed_size, 1) > 200
            ):
                raise ValueError("Entry exceeds the compression-ratio limit.")
            total += len(content)
            if total > MAX_ARCHIVE_BYTES:
                raise InputError("Recovered ZIP data exceeds 50 MiB.")
            output[name] = content
            position = end
        except (ValueError, zlib.error) as exc:
            notes.append(f"{name[:120]}: {exc}")
    if not output:
        raise InputError("No complete, CRC-verified ZIP entries could be recovered.")
    return output, notes


def zip_contents(raw: bytes) -> tuple[dict[str, bytes], list[str], str]:
    try:
        archive = open_zip(raw)
    except zipfile.BadZipFile:
        recovered, notes = salvage_zip(raw)
        return (
            recovered,
            ["The central directory was missing. Used local entry headers.", *notes],
            "local headers",
        )
    recovered, notes = {}, []
    with archive:
        for info in archive.infolist():
            mode = (info.external_attr >> 16) & 0o170000
            if info.is_dir():
                continue
            if (
                not archive_name_ok(info.filename)
                or mode == 0o120000
                or info.flag_bits & 1
            ):
                notes.append(
                    f"Skipped unsafe, linked, or encrypted entry: {info.filename[:120]}"
                )
                continue
            if info.filename in recovered:
                notes.append(f"Skipped repeated entry: {info.filename[:120]}")
                continue
            try:
                recovered[info.filename] = archive.read(info)
            except (
                zipfile.BadZipFile,
                RuntimeError,
                NotImplementedError,
                zlib.error,
            ) as exc:
                notes.append(f"{info.filename[:120]}: {str(exc)[:160]}")
    return recovered, notes, "central directory"


def entropy(raw: bytes) -> float:
    sample = raw[:1_048_576]
    if not sample:
        return 0.0
    return round(
        -sum(
            (n / len(sample)) * math.log2(n / len(sample))
            for n in Counter(sample).values()
        ),
        3,
    )


def inspect(raw: bytes, name: str) -> dict:
    if len(raw) > MAX_FILE_BYTES:
        raise InputError("This file exceeds 25 MiB.")
    detected = identify(raw, name)
    report = {
        "name": name,
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "detected": detected,
        "entropy": entropy(raw),
        "checks": [],
        "repair_available": False,
        "repair_label": "",
        "status": "review",
        "details": {},
    }

    def add(label, status, detail):
        report["checks"].append({"label": label, "status": status, "detail": detail})

    if not raw:
        add("File content", "fail", "The file is empty. There are no bytes to recover.")
        report["status"] = "unrecoverable"
        return report
    ext = Path(name).suffix.lower()
    aliases = {".jpeg": ".jpg", ".tsv": ".csv"}
    expected = detected["extension"]
    if expected and aliases.get(ext, ext) != aliases.get(expected, expected):
        add(
            "File extension",
            "warning",
            f'The bytes suggest {expected}; the name ends with {ext or "no extension"}.',
        )
    else:
        add("File signature", "pass", detected["basis"])
    kind = detected["kind"]
    try:
        if kind == "json":
            text, encoding = decode_text(raw)
            try:
                value = json.loads(text)
                add(
                    "JSON syntax",
                    "pass",
                    f"Valid JSON. Root type: {type(value).__name__}.",
                )
            except json.JSONDecodeError as exc:
                add(
                    "JSON syntax",
                    "fail",
                    f"{exc.msg} at line {exc.lineno}, column {exc.colno}.",
                )
                fixed, removed = trailing_comma_fix(text)
                json.loads(fixed)
                add(
                    "Conservative repair",
                    "pass",
                    f"Removing {removed} trailing commas produces valid JSON.",
                )
            report["repair_available"], report["repair_label"] = (
                True,
                "Write valid JSON copy",
            )
            report["details"]["encoding"] = encoding
        elif kind in {"csv", "tsv"}:
            text, encoding = decode_text(raw)
            rows, delimiter = read_csv(text)
            widths = sorted(set(map(len, rows)))
            add(
                "CSV structure",
                "pass" if len(widths) <= 1 else "warning",
                f"{len(rows)} rows. Row widths: {widths}. Delimiter: {repr(delimiter)}.",
            )
            report["details"].update(
                {
                    "rows": len(rows),
                    "widths": widths,
                    "delimiter": delimiter,
                    "encoding": encoding,
                }
            )
            report["repair_available"], report["repair_label"] = (
                True,
                "Normalize CSV copy",
            )
        elif kind in {"zip", "docx", "xlsx", "pptx"}:
            entries, notes, method = zip_contents(raw)
            add(
                "Readable archive entries",
                "pass" if entries else "fail",
                f"{len(entries)} CRC-verified entries using {method}.",
            )
            for note in notes:
                add("Archive coverage", "warning", note)
            report["details"]["entries"] = [
                {"name": n, "bytes": len(v)} for n, v in entries.items()
            ]
            report["repair_available"], report["repair_label"] = (
                bool(entries),
                "Rebuild readable archive entries",
            )
        elif kind == "png":
            chunks = png_chunks(raw)
            invalid = [c["type"] for c in chunks if not c["crc_ok"]]
            add(
                "PNG chunk checksums",
                "fail" if invalid else "pass",
                (
                    f"Invalid checksums: {invalid}"
                    if invalid
                    else f"All {len(chunks)} chunk checksums match."
                ),
            )
            report["details"]["chunks"] = chunks
            if not invalid:
                report["repair_available"], report["repair_label"] = (
                    True,
                    "Write verified PNG copy",
                )
        elif kind == "pdf":
            add(
                "PDF end marker",
                "pass" if b"%%EOF" in raw[-2048:] else "warning",
                (
                    "End marker found."
                    if b"%%EOF" in raw[-2048:]
                    else "End marker is missing from the last 2 KiB."
                ),
            )
            add(
                "PDF coverage",
                "warning",
                "This core inspector checks markers, not page rendering or PDF object integrity.",
            )
        elif kind == "xml":
            safe_xml(raw)
            add(
                "XML syntax",
                "pass",
                "The XML parser accepted this document without document types or entities.",
            )
        elif kind in {"txt", "md"}:
            text, encoding = decode_text(raw)
            if "\x00" in text:
                raise InputError("The text contains null bytes.")
            add("Text encoding", "pass", f"Read using {encoding}.")
            report["repair_available"], report["repair_label"] = (
                True,
                "Write UTF-8 text copy",
            )
        else:
            add(
                "Repair coverage",
                "warning",
                "This file type has no implemented repair method. The original remains unchanged.",
            )
    except (
        ValueError,
        UnicodeError,
        csv.Error,
        zipfile.BadZipFile,
        struct.error,
        zlib.error,
    ) as exc:
        add("Format validation", "fail", str(exc)[:300])
    statuses = {check["status"] for check in report["checks"]}
    report["status"] = (
        "repairable"
        if "fail" in statuses and report["repair_available"]
        else (
            "damaged"
            if "fail" in statuses
            else "review" if "warning" in statuses else "valid"
        )
    )
    return report


def repair(
    raw: bytes, name: str, *, escape_formulas: bool = True
) -> tuple[bytes, str, list[str]]:
    report = inspect(raw, name)
    if not report["repair_available"]:
        raise InputError("No safe implemented repair is available for this file.")
    kind, notes = report["detected"]["kind"], []
    if kind == "json":
        text, _ = decode_text(raw)
        fixed, count = trailing_comma_fix(text)
        value = json.loads(fixed)
        notes.append(
            f"Removed {count} trailing commas. No keys or values were invented."
        )
        return (
            (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
            ".json",
            notes,
        )
    if kind in {"csv", "tsv"}:
        text, _ = decode_text(raw)
        rows, delimiter = read_csv(text)
        width = max(map(len, rows), default=0)
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        padded, formulas = 0, 0
        for row in rows:
            padded += width - len(row)
            cleaned = []
            for value in row:
                if escape_formulas and value.lstrip().startswith(
                    ("=", "+", "-", "@", "\t", "\r")
                ):
                    value = "'" + value
                    formulas += 1
                cleaned.append(value)
            writer.writerow(cleaned + [""] * (width - len(row)))
        notes.extend(
            [
                f"Converted delimiter {repr(delimiter)} to comma.",
                f"Added {padded} empty cells. No existing cell was discarded.",
                f"Escaped {formulas} formula-like values for safer spreadsheet opening.",
            ]
        )
        return stream.getvalue().encode("utf-8-sig"), ".csv", notes
    if kind in {"zip", "docx", "xlsx", "pptx"}:
        entries, notes, _ = zip_contents(raw)
        result = io.BytesIO()
        with zipfile.ZipFile(result, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for entry, content in entries.items():
                archive.writestr(entry, content)
        # Recovered Office packages are archives, not certified working documents.
        if kind != "zip":
            notes.append(
                "The recovered Office parts are saved as ZIP. Document layout and application behavior were not verified."
            )
        notes.append(
            f"Recovered {len(entries)} readable entries. Missing or skipped entries are not reconstructed."
        )
        return result.getvalue(), ".zip", notes
    if kind == "png":
        chunks = png_chunks(raw)
        notes.append(
            "Copied verified PNG bytes through the end chunk. Image content was not guessed or redrawn."
        )
        return raw[: chunks[-1]["end"]], ".png", notes
    if kind in {"txt", "md"}:
        text, encoding = decode_text(raw)
        notes.append(
            f"Converted {encoding} text to UTF-8. Line endings were preserved."
        )
        return text.encode("utf-8"), ".txt" if kind == "txt" else ".md", notes
    raise InputError("This repair method is not implemented.")


def hex_view(raw: bytes, offset: int = 0, count: int = 256) -> list[dict]:
    rows = []
    for start in range(offset, min(len(raw), offset + count), 16):
        block = raw[start : start + 16]
        rows.append(
            {
                "offset": f"{start:08X}",
                "hex": " ".join(f"{b:02X}" for b in block),
                "text": "".join(chr(b) if 32 <= b <= 126 else "." for b in block),
            }
        )
    return rows


_core_inspect = inspect
_core_repair = repair


def inspect(raw: bytes, name: str) -> dict:
    """Combine byte-level checks with isolated native-format validation."""
    report = _core_inspect(raw, name)
    from .advanced import native_kind, NATIVE, request

    kind = native_kind(raw, name, report["detected"]["kind"])
    if kind not in NATIVE:
        return report
    report["detected"]["kind"] = kind
    try:
        result = request(raw, name)
        report["details"].update(result["details"])
        report["checks"].append(
            {
                "label": "Native format validation",
                "status": "pass",
                "detail": "; ".join(result["notes"]),
            }
        )
        report["repair_available"] = True
        report["repair_label"] = "Create verified " + kind.upper() + " copy"
        report["status"] = "review"
    except (InputError, ValueError) as exc:
        report["checks"].append(
            {"label": "Native format validation", "status": "fail", "detail": str(exc)}
        )
        report["repair_available"] = False
        report["status"] = "damaged"
    return report


def repair(
    raw: bytes, name: str, *, escape_formulas: bool = True
) -> tuple[bytes, str, list[str]]:
    from .advanced import native_kind, NATIVE, request, office_copy

    kind = native_kind(raw, name, identify(raw, name)["kind"])
    if kind in NATIVE:
        result = request(raw, name, recover=True)
        return result["content"], result["extension"], result["notes"]
    if kind in {"docx", "xlsx", "pptx"}:
        return office_copy(raw, kind)
    return _core_repair(raw, name, escape_formulas=escape_formulas)
