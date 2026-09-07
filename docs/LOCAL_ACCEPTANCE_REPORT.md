# RecoveryLab: local acceptance report

Status: PARTIAL. New evidence from this PC, not the committed release reports.

Repository: https://github.com/danial-maqbool/RecoveryLab
Initial commit: `d0c5e47bad31a480f56da1ee791ccead7940eb95`.
Tested source commit: `da24aa63188e850df9c9bc25bd9b738b738a3bcd`. Source tree was clean for the final source checks; empty uncommitted diff SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. Subsequent report-only edits are listed in Git.
Initial branch: `main`. Existing changes: none. Missing repository cloned as a sibling.
Validation branch: `local-validation/20260907-acceptance-01`.
OS and architecture: Windows 11 Home build 26200, AMD64. Python 3.14.3, independent project-local `.venv`.
Native tools: Tesseract 5.4.0.20240606, eng and osd; FFmpeg/ffprobe 8.1.2; Playwright 1.57.0, Chromium 143.0.7499.4.
Run date: 2026-09-07, Asia/Karachi. About 412 GB free at initial inspection.
Resolved runtime requirements: `runtime-early/freeze.log`; development versions in `development/freeze.log` or `development-early/freeze.log`.
All evidence paths below are relative to ignored `artifacts/local-qa/20260907-acceptance-01/`.

## Results

| Gate or case ID | Status | Command and exit code | Evidence path | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Runtime-only install | PASS | Bootstrap, preflight, pip check, sample: 0 | `runtime/bootstrap.log`, `runtime-early/` | Sample before dev tools. |
| Direct package and native checks | PASS | Dev bootstrap, native preflight, pip check: 0 | `development/`, `development-early/`, `normal-launcher-doctor.log` | Own interpreter per repo. |
| Full Windows suite | BLOCKED | `verify.py --strict`: 1 | `final-suite/test-report.json` | 133 run, 130 passed, 3 skipped, 0 failures/errors. Strict gate does not pass. |
| Direct-browser checks | PASS | `browser_check.py --slow-api --record`: 0 | `final-browser/` | 19 checks, real loopback backend/downloads. |
| Interaction | PASS | `browser_interaction_check.py`: 0 | `final-interaction/` | Real UI job module, progress, cancellation, navigation and Escape dialog. |
| Offline runtime | PASS | Network-disabled Docker: 0 | `offline-02/` | Linux container on this PC: 133 run, 133 passed, 0 skipped, 19 browser checks. |
| Encryption and restore | PASS | Acceptance runner and suite | `final-acceptance/results.json` | Unique persistent synthetic data directory. |
| Clean clone/setup | PASS | Clone main, bootstrap, launcher: 0 | `initial-state.json`, runtime logs | No older ZIP or cross-project runtime dependency. |
| Missing native dependency | PASS | Process-local empty PATH OCR request: 0 | `missing-native/result.json` | Clear OCR/Tesseract error. |
| Windows source/vault symlink | BLOCKED | Strict-suite skips | Suite report | Account cannot create symlinks; isolated Linux checks pass. |
| POSIX ciphertext mode on Windows | NOT APPLICABLE | Platform skip | Suite report | Executed in Linux container. |
| RL-01 | PASS | Commands below and evidence logs | `final-browser; final-acceptance/results.json` | Five sample batch copies finish; real downloads/reports match backend bytes; signatures and hex view checked. |
| RL-02 | PASS | Commands below and evidence logs | `final-suite/verify.log` | JSON/JSONL, malformed records, CSV quoting/ragged rows/formula escaping and legacy encoding; unsupported repairs rejected. |
| RL-03 | PASS | Commands below and evidence logs | `final-suite; supplemental-archives/results.json` | Missing directory, truncated entry, CRC, unsafe/encrypted entries and expansion; omissions verified. Nested ZIP stays byte-identical without recursive extraction. |
| RL-04 | PASS | Commands below and evidence logs | `extended-02/office-independent-render; final-acceptance` | DOCX/XLSX/PPTX opened and rendered by Microsoft Office 16; PDF independently rendered. Values preserved. Default spreadsheet column width clips text visually; logical cell remains intact. |
| RL-05 | PASS | Commands below and evidence logs | `final-acceptance/results.json; final-suite` | PNG/JPEG/GIF pixels independently decoded by Chromium; missing/invalid pixel data rejected. |
| RL-06 | PASS | Commands below and evidence logs | `final-acceptance/results.json` | SQLite integrity, table/BLOB bytes, source hashes and Windows handle cleanup. |
| RL-07 | PASS | Commands below and evidence logs | `final-acceptance; extended-02/video-playback.json; final-suite` | FFmpeg remux, streams/duration, frame decode and Chromium playback: one second, 160x120, ten decoded frames. Network input/playlist rejection tested. |
| RL-08 | PASS | Commands below and evidence logs | `final-interaction; final-suite; readonly-destination-03/result.json` | Cancellation, occupied names, malformed inputs and failed workers. Windows ACL-denied export fails without output or changed sources; test ACL restored. |
| Native login service/desktop input | NOT APPLICABLE | No project acceptance case | `docs/LOCAL_TESTING.md` | No login task or desktop control installed. |

### Commands and evidence interpretation

Run in the repository root. Replace `<new-dir>` with a new ignored run directory. Preserve all failed evidence.

```powershell
py -3 bootstrap.py
.\.venv\Scripts\python.exe scripts/preflight.py --report-dir <new-dir>
.\.venv\Scripts\python.exe -m pip check
.\start.bat --demo --no-browser --port 0
py -3 bootstrap.py --dev
.\.venv\Scripts\python.exe scripts/preflight.py --tests --require-native --report-dir <new-dir>
.\.venv\Scripts\python.exe -m pip freeze
.\.venv\Scripts\python.exe scripts/verify.py --strict --report-dir <new-dir>
.\.venv\Scripts\python.exe scripts/browser_check.py --slow-api --record --report-dir <new-dir>
.\.venv\Scripts\python.exe scripts/acceptance_check.py --report-dir <new-dir>
.\.venv\Scripts\python.exe scripts/browser_interaction_check.py --report-dir <new-dir>
```

Command JSON beside logs records exact arguments, exit codes, start times and durations. Preflight, suite, browser and worker reports use separate directories. Late `runtime/` reruns outside LocalFlow occurred after development installation; the initial `runtime-early/` evidence is the valid runtime-only proof.

Browser evidence covers light/dark themes, narrow/wide layouts, navigation, visible keyboard focus, real downloads and parsed bytes. All acceptance uses direct loopback navigation. Interaction checks invoke the real UI job module and backend; they do not prove every physical keyboard/device or OS adapter.

The bounded sample took 0.314 seconds, with 31580160 bytes peak working set in the actual in-process Python test interpreter. This includes test imports and excludes native child workers and interpreter startup. It is not a whole-application benchmark. See `performance-02/performance.json`. The earlier `performance/` measured the Windows venv launcher and is not a valid application-memory measurement.

### Offline evidence

Setup downloads preceded isolation. An unprivileged Linux container used Docker `--network none`, read-only source and a writable synthetic evidence mount, with bounded CPU/memory/process limits. A reserved-address probe failed with ENETUNREACH. `strace -f` observed backend tests and browser/backend processes. Backend destinations were loopback only. Chromium DNS attempts to the container resolver failed with ENETUNREACH. No successful outbound runtime connection was observed. Browser-only assertions were not used as backend proof. No host firewall change or neural model download.

The first container attempt lacked a named account/home for its numeric UID and browser profile. Those environment failures remain in `offline-01/`. The corrected image has a real unprivileged user/home. Container success is not Windows native-session acceptance.

## Defects and regression tests

1. Windows checkout line endings caused false source-manifest failures. `scripts/materialize.py` now canonicalizes CRLF only for recognized text without NUL bytes. Binary hashes remain exact. Two `tests/test_manifest.py` regressions cover text and binary content. The text regression failed before the fix and passed after it. Manifest hashes were refreshed after source review.
2. The browser checker could inspect state before a pending POST finished. API-request tracking and a quiet interval now gate assertions. Real delayed-API browser runs retain feature assertions. Saved downloads are compared with authenticated backend bytes and parsed. An initial attachment-response-body comparison was a harness error; that failed evidence remains.
3. Project-local acceptance and interaction scripts retain fixtures, outputs and hashes. Vendored localdesk copies were compared; no shared runtime module or project-specific runtime behavior was replaced.

## Skips and blocked checks

- `tests.test_safety.SafetyTests.test_symlink_input_is_rejected`: This OS account cannot create symbolic links.
- `tests.test_vault.VaultTests.test_ciphertext_file_permissions`: POSIX mode test.
- `tests.test_vault.VaultTests.test_vault_symlink_is_rejected`: Creating symbolic links may need a Windows developer setting.

Native login tasks, OS keyring persistence and title/input adapters were not exercised in the active profile. Unit/mock adapter checks are not native acceptance. Optional neural models were NOT RUN by design; automatic downloads were prohibited and the built-in statistical backend was tested.

## Source and output safety

Only synthetic documents and browser databases were used. Origins, initial commits and clean status were recorded. Acceptance fixtures and outputs have hashes; browser download evidence records saved byte hashes. Historical release reports, screenshots and GIFs were preserved. Vaults, passphrases, exports, caches, raw logs and private absolute paths are not committed.

Only owned launchers, backends, browser contexts, containers and Office instances were stopped. No personal Office document or browser history was read. No login service or saved OS credential was created. Existing Tesseract was added to user PATH with the previous value retained locally; new terminals inherit it. No machine-wide PATH or global firewall/security setting was changed.

README commands and relative documentation links were checked: no broken local targets or README em dashes. Each app remains independently installable. Staged changes were checked for secrets/private paths before normal branch pushes. GitHub CI is separate evidence; the five-project summary records exact pushed heads and checks.

## User actions

1. Provide a disposable Windows profile/session with permission to create symbolic links, then rerun both skipped symlink tests and the strict suite there. No global security setting was changed.

## Source CI

PASS: [Tests workflow](https://github.com/danial-maqbool/RecoveryLab/actions/runs/34131872343) at `da24aa63188e850df9c9bc25bd9b738b738a3bcd`. This is remote CI, separate from local acceptance.

## Decision

PARTIAL. No claim that all applicable Windows acceptance gates passed. Automated and browser successes do not remove native-session blockers.
