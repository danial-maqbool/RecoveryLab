"""Native-format recovery and subprocess regression tests."""

import gzip
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
from unittest.mock import patch
from app.formats import inspect, repair
from app.advanced import office_copy, request
from localdesk.safety import InputError, digest
from tests.fixtures import make_pdf
from tests.support import AppCase, zipped


class NativeRecoveryTests(AppCase):
    def test_pdf_roundtrip_retains_text(self):
        from pypdf import PdfReader

        p = make_pdf(self.workspace / "page.pdf", text="Recovered invoice 42")
        report = inspect(p.read_bytes(), p.name)
        self.assertTrue(report["repair_available"], report)
        data, extension, notes = repair(p.read_bytes(), p.name)
        self.assertEqual(extension, ".pdf")
        self.assertIn(
            "Recovered invoice 42",
            PdfReader(io.BytesIO(data), strict=True).pages[0].extract_text(),
        )
        self.assertTrue(notes)

    def test_encrypted_pdf_requires_password(self):
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(200, 200)
        writer.encrypt("test-pass")
        stream = io.BytesIO()
        writer.write(stream)
        with self.assertRaises(InputError):
            repair(stream.getvalue(), "protected.pdf")

    def test_jpeg_copy_decodes_pixels(self):
        from PIL import Image

        stream = io.BytesIO()
        Image.new("RGB", (32, 24), "white").save(stream, format="JPEG")
        data, extension, notes = repair(stream.getvalue(), "picture.jpg")
        self.assertEqual(extension, ".png")
        with Image.open(io.BytesIO(data)) as output:
            self.assertEqual(output.size, (32, 24))
            output.verify()

    def test_gif_reports_first_frame(self):
        from PIL import Image

        a, b = Image.new("RGB", (20, 20), "red"), Image.new("RGB", (20, 20), "blue")
        stream = io.BytesIO()
        a.save(stream, format="GIF", save_all=True, append_images=[b])
        data, extension, notes = repair(stream.getvalue(), "animation.gif")
        self.assertEqual(extension, ".png")
        self.assertIn("first frame", " ".join(notes))

    def test_jsonl_reports_excluded_lines(self):
        data, extension, notes = repair(
            b'{"first":1}\n{"broken":\n{"last":3}\n', "records.jsonl"
        )
        self.assertEqual(extension, ".jsonl")
        self.assertEqual(
            [json.loads(s) for s in data.splitlines()], [{"first": 1}, {"last": 3}]
        )
        self.assertIn("2", " ".join(notes))

    def test_jsonl_with_no_complete_record_is_rejected(self):
        with self.assertRaises(InputError):
            repair(b"{broken", "records.ndjson")

    def test_gzip_crc_checked(self):
        raw = gzip.compress(b"surviving bytes")
        output, ext, notes = repair(raw, "data.gz")
        self.assertEqual(output, b"surviving bytes")
        self.assertEqual(ext, ".bin")
        with self.assertRaises(InputError):
            repair(raw[:-4] + b"FAIL", "broken.gz")

    def test_sqlite_copy_preserves_rows_and_schema(self):
        p = self.workspace / "input.sqlite3"
        with sqlite3.connect(p) as db:
            db.execute("CREATE TABLE entries(id INTEGER PRIMARY KEY, value BLOB)")
            db.execute("CREATE INDEX ix ON entries(value)")
            db.execute("INSERT INTO entries VALUES(?,?)", (8, b"\x00binary"))
        original = digest(p)
        data, extension, notes = repair(p.read_bytes(), p.name)
        q = self.workspace / ("copy" + extension)
        q.write_bytes(data)
        with sqlite3.connect(q) as db:
            self.assertEqual(
                db.execute("SELECT id,value FROM entries").fetchone(),
                (8, b"\x00binary"),
            )
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertIsNotNone(
                db.execute("SELECT name FROM sqlite_master WHERE name='ix'").fetchone()
            )
        self.assertEqual(digest(p), original)

    def test_office_extension_requires_minimum_structure(self):
        data, ext, notes = office_copy(zipped({"word/document.xml": "<doc/>"}), "docx")
        self.assertEqual(ext, ".zip")
        self.assertIn("missing", " ".join(notes))

    def test_office_copy_is_readable_by_docx(self):
        from docx import Document

        document = Document()
        document.add_paragraph("Retain this paragraph.")
        stream = io.BytesIO()
        document.save(stream)
        data, ext, notes = repair(stream.getvalue(), "report.docx")
        self.assertEqual(ext, ".docx")
        self.assertEqual(
            Document(io.BytesIO(data)).paragraphs[0].text, "Retain this paragraph."
        )

    def test_worker_timeout_returns_clear_error(self):
        with patch(
            "app.advanced.subprocess.run",
            side_effect=subprocess.TimeoutExpired("test", 60),
        ):
            with self.assertRaisesRegex(InputError, "60 second"):
                request(b"%PDF-", "page.pdf")

    def test_worker_output_is_checked(self):
        with patch(
            "app.advanced.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, "not json", ""),
        ):
            with self.assertRaisesRegex(InputError, "invalid data"):
                request(b"%PDF-", "page.pdf")

    def test_actual_video_remux(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("FFmpeg and ffprobe are required for this integration test.")
        source = self.workspace / "clip.mp4"
        subprocess.run(
            [
                shutil.which("ffmpeg"),
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=white:s=64x64:d=0.2",
                "-c:v",
                "mpeg4",
                "-y",
                str(source),
            ],
            check=True,
            capture_output=True,
            timeout=20,
        )
        data, extension, notes = repair(source.read_bytes(), source.name)
        self.assertEqual(extension, ".mkv")
        self.assertTrue(data.startswith(b"\x1aE\xdf\xa3"))
        self.assertIn("Missing packets", " ".join(notes))
