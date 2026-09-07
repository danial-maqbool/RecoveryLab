"""Conservative format recovery with hostile-entry and source integrity checks."""

import io
import json
import zipfile
from app.formats import (
    entropy,
    hex_view,
    identify,
    inspect,
    repair,
    trailing_comma_fix,
    zip_contents,
)
from localdesk.safety import InputError, digest
from tests.support import AppCase, ROOT, zipped


class RecoveryTests(AppCase):
    def test_signature_beats_wrong_extension(self):
        self.assertEqual(identify(b"%PDF-1.4\n", "fake.txt")["kind"], "pdf")

    def test_json_structure_is_identified(self):
        self.assertEqual(identify(b'{"a":1}', "unknown.dat")["kind"], "json")

    def test_unknown_binary_is_not_assumed_text(self):
        self.assertEqual(identify(b"\x00\x01\x02", "file.dat")["kind"], "unknown")

    def test_trailing_comma_repair_preserves_string(self):
        text = '{"a":"comma,] text","b":[1,2,],}'
        fixed, count = trailing_comma_fix(text)
        self.assertEqual(count, 2)
        self.assertEqual(json.loads(fixed)["a"], "comma,] text")

    def test_escaped_quote_does_not_break_repair(self):
        text = r'{"a":"a\"b,]","b":1,}'
        fixed, _ = trailing_comma_fix(text)
        self.assertEqual(json.loads(fixed)["b"], 1)

    def test_valid_json_has_checked_status(self):
        self.assertEqual(inspect(b'{"a":1}', "file.json")["status"], "valid")

    def test_broken_json_returns_repairable(self):
        self.assertEqual(inspect(b'{"a":1,}', "file.json")["status"], "repairable")

    def test_arbitrary_broken_json_is_not_reconstructed(self):
        with self.assertRaises((InputError, ValueError)):
            repair(b'{"missing":', "file.json")

    def test_repaired_json_parses(self):
        raw, ext, notes = repair(b'{"a":[1,2,],}', "file.json")
        self.assertEqual(json.loads(raw), {"a": [1, 2]})
        self.assertEqual(ext, ".json")

    def test_legacy_text_becomes_utf8(self):
        raw, ext, notes = repair(b"caf\xe9", "legacy.txt")
        self.assertEqual(raw.decode("utf-8"), "café")

    def test_csv_preserves_extra_columns(self):
        raw, ext, notes = repair(b"A;B\n1;2;3\n4\n", "uneven.csv")
        self.assertIn("3", raw.decode("utf-8-sig"))
        self.assertIn("4", raw.decode("utf-8-sig"))

    def test_csv_formula_cells_are_escaped(self):
        raw, _, _ = repair(b"Name,Value\nA,=1+1\n", "table.csv")
        self.assertIn("'=1+1", raw.decode("utf-8-sig"))

    def test_zip_without_directory_is_recovered(self):
        raw = zipped({"one.txt": "First", "two.txt": "Second"})
        raw = raw[: raw.index(b"PK\x01\x02")]
        content, ext, notes = repair(raw, "damaged.zip")
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            self.assertEqual(archive.read("one.txt"), b"First")
            self.assertEqual(archive.read("two.txt"), b"Second")

    def test_zip_traversal_member_is_excluded(self):
        content, _, _ = repair(
            zipped({"../outside.txt": "bad", "good.txt": "good"}), "input.zip"
        )
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            self.assertEqual(archive.namelist(), ["good.txt"])

    def test_crc_damaged_zip_entry_is_not_invented(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as z:
            z.writestr("bad.txt", b"UNIQUE_PAYLOAD")
        raw = stream.getvalue().replace(b"UNIQUE_PAYLOAD", b"BROKEN_PAYLOA_")
        files, notes, method = zip_contents(raw)
        self.assertEqual(files, {})

    def test_pdf_has_no_fake_repair(self):
        report = inspect(b"%PDF-1.4\n%%EOF", "x.pdf")
        self.assertFalse(report["repair_available"])
        with self.assertRaises(InputError):
            repair(b"%PDF-1.4\n%%EOF", "x.pdf")

    def test_entropy_is_real_and_bounded(self):
        self.assertEqual(entropy(b"aaaa"), 0)
        self.assertAlmostEqual(entropy(bytes(range(256))), 8, places=4)

    def test_hex_view_bounds(self):
        self.assertEqual(hex_view(b"abc", 100), [])
        self.assertTrue(hex_view(b"abc", 0))

    def test_inspect_repair_api_preserves_source(self):
        p = self.file("broken.json", b'{"a":1,}')
        h = digest(p)
        result = self.finish("inspect", {"paths": [str(p)]})
        ident = result["inspections"][0]["id"]
        fixed = self.finish("repair", {"id": ident})
        self.assertTrue(fixed["original_unchanged"])
        self.assertEqual(digest(p), h)
        self.assertEqual(json.loads(self.output(fixed["output"])), {"a": 1})

    def test_changed_source_blocks_repair(self):
        p = self.file("broken.json", b'{"a":1,}')
        result = self.finish("inspect", {"paths": [str(p)]})
        p.write_text('{"a":2,}')
        job = self.finish(
            "repair", {"id": result["inspections"][0]["id"]}, expected="failed"
        )
        self.assertIn("source changed", job["error"])

    def test_inspection_report_has_no_probability(self):
        r = inspect(b"{}", "x.json")
        self.assertNotIn("probability", r)
        self.assertNotIn("confidence", r)
