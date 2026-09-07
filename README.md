# RecoveryLab

A file can fail for several reasons. Start with an inspection, read the findings, and create a recovered copy only when a supported method exists. RecoveryLab keeps the original bytes unchanged.

**Local processing. No API keys. No account. CPU operation. Encrypted application database.**

[![Tests](https://github.com/danial-maqbool/RecoveryLab/actions/workflows/tests.yml/badge.svg)](https://github.com/danial-maqbool/RecoveryLab/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab)
![Version](https://img.shields.io/badge/version-0.2.0-087f76)
![License](https://img.shields.io/badge/license-MIT-2e805b)

![Recorded RecoveryLab interface](docs/assets/demo.gif)

The recording uses synthetic examples in the working application. Frame timing is illustrative.

## What you can do

| Feature | Behavior |
| :--- | :--- |
| **Binary inspection** | Identify signatures, compare extensions, inspect checksums, and read a hex preview. |
| **Text recovery** | Normalize JSON, JSONL, CSV, and text encodings. Never invent missing values. |
| **ZIP recovery** | Rebuild CRC-verified entries. Recover supported entries when the central directory is missing. |
| **Document recovery** | Rebuild readable PDF pages and supported Office packages. Report omitted parts and validation results. |
| **Image recovery** | Decode surviving image data into a new PNG. Validate the output before returning it. |
| **Database recovery** | Copy readable SQLite table data into a new database. Report unreadable tables. |
| **Video recovery** | Use local FFmpeg to remux readable streams. No network protocols are enabled. |
| **Batch processing** | Inspect and recover multiple files with individual outcomes and source-integrity checks. |

## Start on your PC

Install Python 3.11 or later. Download this repository or clone it:

```sh
git clone https://github.com/danial-maqbool/RecoveryLab.git
cd RecoveryLab
```

**Windows**

```powershell
py -3 bootstrap.py
.\start.bat
```

**Linux or macOS**

```sh
python3 bootstrap.py
sh start.sh
```

Setup creates a project-local `.venv`. The first normal start asks for a vault passphrase with at least 12 characters. Keep the passphrase. There is no password-reset server.

The application opens at `http://127.0.0.1:8763`. Try synthetic data without a persistent database:

```sh
# Windows
start.bat --demo

# Linux or macOS
sh start.sh --demo
```

The first package installation needs internet access or pre-downloaded wheels. Normal processing stays local. Install Tesseract and its local language data for OCR. RecoveryLab also uses FFmpeg and ffprobe for video recovery. Read [Setup](docs/SETUP.md) for OS instructions and offline installation.

## Daily use

Read the [user guide](docs/USER_GUIDE.md). Start with the included examples. Select your files only after checking the example outputs.

Closing the browser leaves the local Python process running. Press Ctrl+C in its terminal to stop it. A user-login service can keep selected background jobs running without an open terminal. Service installation is explicit and uses the OS credential store. See [Background operation](docs/BACKGROUND.md).

## Where your data goes

| Location | Contents |
| :--- | :--- |
| `.local-data/app.vault` | Authenticated encrypted database snapshot. |
| `.local-data/inbox/` | Files explicitly uploaded or pasted into the application. |
| `.local-data/exports/` | New outputs and reports. |
| OS credential store | Vault passphrase only after explicit service setup. |

SQLite works in memory. The application encrypts persistent database snapshots and database backups with AES-256-GCM. Source files, exported files, and parser temporary files are not encrypted by the application. Protect those files with OS disk encryption when needed.

## Design

```mermaid
flowchart LR
    A[Local browser] --> B[Loopback API and session checks]
    B --> C[Bounded job queue]
    C --> D[Project operations]
    D --> E[New output copies]
    C --> F[In-memory SQLite]
    F --> G[Encrypted vault]
```

```text
app/          Project operations and validation
localdesk/    Local HTTP, jobs, vault, OCR/PDF, and semantic components
web/          HTML, CSS, and JavaScript without external runtime assets
examples/     Synthetic input files
tests/        Unit, integration, and adversarial regression tests
scripts/      Browser checks and release verification
docs/         Setup, API, design, reports, and recorded media
```

Each repository contains its runtime source. No other repository is required after cloning. The shared runtime has a recorded source revision in [Runtime provenance](docs/RUNTIME.md).

## Verify a change

```sh
# Use .venv\Scripts\python.exe on Windows.
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/verify.py
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/browser_check.py
```

The CI matrix runs on Windows, macOS, and Ubuntu with Python 3.11 and 3.13. Ubuntu also runs native-tool integration tests and a direct-navigation browser check. Reports list every skipped test. Read [Verification](docs/VERIFICATION.md) before drawing conclusions from a test count.

## Processing boundaries

Recovery uses surviving data. It cannot recreate missing bytes without a reference. A readable file can still contain incomplete content. Review recovery notes and open the output in its normal application. This tool is not a malware-removal product.

Passing tests does not prove that all inputs or computers work. Read [Security](SECURITY.md) and [Processing boundaries](docs/LIMITS.md).

## Documentation

[User guide](docs/USER_GUIDE.md) · [Setup](docs/SETUP.md) · [API](docs/API.md) · [Architecture](docs/ARCHITECTURE.md) · [Verification](docs/VERIFICATION.md) · [Contributing](CONTRIBUTING.md)

## License

MIT. See [LICENSE](LICENSE). External tools and model weights keep their own licenses. See [Sources](docs/SOURCES.md).
