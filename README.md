# RecoveryLab

Inspect damaged files and create a recovered copy when a safe method is available.

[![Tests](https://github.com/danial-maqbool/RecoveryLab/actions/workflows/tests.yml/badge.svg)](https://github.com/danial-maqbool/RecoveryLab/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab)
![Version](https://img.shields.io/badge/version-0.2.0-087f76)
![License](https://img.shields.io/badge/license-MIT-2e805b)

![RecoveryLab demo](docs/assets/demo.gif)

RecoveryLab is a local recovery workbench. It inspects a file first, explains what looks wrong, and only offers recovery methods that the app can check. The original file is never edited in place.

## Main features

- File signature, checksum, structure, and hex inspection
- JSON, JSONL, CSV, text, and encoding recovery
- ZIP recovery for readable entries
- PDF and Office package reconstruction
- Image decode and re-encode recovery
- SQLite readable-row recovery
- Local FFmpeg video remuxing
- Batch recovery with reports and source hashes

## Quick start

```bash
git clone https://github.com/danial-maqbool/RecoveryLab.git
cd RecoveryLab
```

**Windows**

```powershell
py -3 bootstrap.py
.\start.bat --demo
```

**Linux / macOS**

```bash
python3 bootstrap.py
sh start.sh --demo
```

Video recovery needs `ffmpeg` and `ffprobe` installed locally.

## Screenshots

<p align="center">
  <img src="docs/assets/screenshot.png" width="49%" alt="RecoveryLab light view">
  <img src="docs/assets/dark-mode.png" width="49%" alt="RecoveryLab dark view">
</p>

## Project layout

```text
app/        inspection and recovery logic
web/        local interface
localdesk/  local runtime, vault and jobs
examples/   sample damaged files
tests/      automated tests
scripts/    verification tools
docs/       setup, design and test notes
```

## Notes

RecoveryLab can only work with data that is still readable. It does not invent missing bytes and it is not a malware-cleaning tool. Important recovered files should be opened in their normal application and checked.

More details: [Setup](docs/SETUP.md) · [User guide](docs/USER_GUIDE.md) · [Architecture](docs/ARCHITECTURE.md) · [Testing](docs/VERIFICATION.md) · [Security](SECURITY.md)

## License

MIT. See [LICENSE](LICENSE).
