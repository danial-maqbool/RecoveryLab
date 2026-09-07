# Changes

## 0.2.0

- Binary inspection: Identify signatures, compare extensions, inspect checksums, and read a hex preview.
- Text recovery: Normalize JSON, JSONL, CSV, and text encodings. Never invent missing values.
- ZIP recovery: Rebuild CRC-verified entries. Recover supported entries when the central directory is missing.
- Document recovery: Rebuild readable PDF pages and supported Office packages. Report omitted parts and validation results.
- Image recovery: Decode surviving image data into a new PNG. Validate the output before returning it.
- Database recovery: Copy readable SQLite table data into a new database. Report unreadable tables.
- Video recovery: Use local FFmpeg to remux readable streams. No network protocols are enabled.
- Batch processing: Inspect and recover multiple files with individual outcomes and source-integrity checks.

The release also includes encrypted storage, request checks, portable output paths, synthetic examples, test reports, and recorded interface media.
