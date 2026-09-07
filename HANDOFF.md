# RecoveryLab: local testing handoff

Handoff revision: 1. Prepared on 2026-09-07. Application version: 0.2.0.

## Status

The application source is published. This handoff prepares a repeatable local acceptance pass.
It does not certify the user PC, native permissions, every input file, or optional neural weights.
Do not remove documented processing boundaries to change the completion status.

The prior release evidence was recorded at `c9d9391fbfa6d3121c2c4e95cee2b2678d46db0c`.
It reports 121 passing full Linux test executions and 14 browser checks.
Those counts are historical. Shared tests occur in each repository. Native-tool and OS-specific skips are recorded separately.
Use current GitHub Actions and new local reports to verify the handoff commit. Do not present the prior counts as a new run.

## Changes in this handoff

`bootstrap.py --dev` installs test tools into this project .venv.
`scripts/preflight.py` checks Python, direct package pins, SQLite FTS5, and applicable native-tool availability.
`--report-dir` keeps local test reports and media separate from committed release evidence.
Browser reports now distinguish started, failed, and completed runs. An interrupted run cannot keep a stale pass report.
Ten handoff regression tests check setup, requirement handling, and report isolation.

## Read order

Read `AGENTS.md`, this file, `handoff.json`, and `docs/LOCAL_TESTING.md` first.
Then read `docs/SETUP.md`, `docs/LIMITS.md`, `SECURITY.md`, and `docs/VERIFICATION.md`.
The full agent brief is in `docs/LOCAL_AGENT_PROMPT.md`.
Use `docs/LOCAL_TEST_RESULTS.template.md` for the sanitized final report.

## Start and verify

Windows PowerShell, from this repository root:

```powershell
py -3 bootstrap.py
.\.venv\Scripts\python.exe scripts/preflight.py --report-dir artifacts/local-qa/runtime
.\start.bat --demo
```

Stop the demo. Then follow the full runtime-only and development-install checks in `docs/LOCAL_TESTING.md`.
The default local port is `8763`. Use `--port 0 --no-browser` for a temporary server on an available port.
Use a unique `--data-dir` for persistence tests. `--demo` uses temporary data and does not prove persistent vault behavior.
Normal startup needs a vault passphrase. Do not put a real passphrase in a command, script, commit, or report.

## Project acceptance scope

| ID | Area | Required evidence |
| :--- | :--- | :--- |
| RL-01 | Inspection and batch recovery | Run all sample cases through the UI. Wait for final batch results. Check signatures, read-only hex offsets, reports, and download artifacts. |
| RL-02 | Text and structured data | Test supported JSON trailing commas, malformed JSON, JSONL, CSV quoting, ragged rows, text encodings, and formula-like spreadsheet values. Unsupported cases must not report successful recovery. |
| RL-03 | ZIP corruption | Test missing central directory, truncated entries, bad CRC, path traversal, encrypted entries, nested archives, and high expansion. Report every omitted entry. |
| RL-04 | PDF and Office | Rebuild supported PDF and Office fixtures. Open each output in its normal application. Compare pages, text, and readable package parts. Structural validation alone is not a rendering test. |
| RL-05 | Images | Recover supported PNG, JPEG, and GIF fixtures. Decode the result independently. Reject missing pixel data rather than inventing content. |
| RL-06 | SQLite | Recover readable tables and binary cells from a synthetic database. Confirm the source hash and database handles after each run. Test Windows cleanup. |
| RL-07 | Video | With local FFmpeg and ffprobe, remux a small synthetic local clip. Check streams, duration, and playback. Reject network URLs and playlists. Missing streams must remain explicit. |
| RL-08 | Failure safety | Test cancellation, occupied output names, read-only destinations, malformed inputs, and a failed worker. Keep originals unchanged. A recovered copy is not a malware-cleaned file. |

## Work that requires the local machine

Test the relevant native adapters on the actual target OS. Do not infer their behavior from mocked tests.
Install required native tools and language data. Check actual outputs with independent parsers or viewers.
Test a clean runtime-only environment, paths with spaces and Unicode, offline operation, and the existing app data migration path when applicable.
Measure local performance with synthetic fixtures. No universal hardware benchmark is claimed.
Use a disposable OS profile for service and credential-store checks. Do not alter the user active desktop without local consent.

## Evidence and Git rules

Keep raw logs, resolved dependency lists, screenshots, and temporary outputs under ignored `artifacts/`.
The committed `docs/test-report.json`, `docs/browser-report.json`, and `docs/platforms/` remain historical release evidence.
New local reports must identify their actual commit and environment. Review evidence before publishing it.
Never commit user documents, browser history, vaults, passwords, API tokens, model weights, or .venv.
Use a local-validation branch. Preserve existing changes. Never force-push or reset user work.

If a shared `localdesk/` defect is fixed, compare all five copies and apply only the relevant patch.
Run each affected repository suite. The apps must remain independently cloneable and runnable.
Do not run `scripts/prepare_release.py` as an installer. Use `bootstrap.py`.
Update source-manifest hashes only after reviewing changes. Preserve real tests and security controls.

## Acceptance decision

Local-machine acceptance: **NOT RUN HERE**.
Use PASS, FAIL, BLOCKED, NOT RUN, or NOT APPLICABLE for each case.
Only state that local acceptance is complete when every applicable gate has evidence.
If a permission blocks one test, record that requirement and continue unrelated tests.

## Local PC acceptance: 2026-09-07

Decision: PARTIAL. See [the current local acceptance report](docs/LOCAL_ACCEPTANCE_REPORT.md).

Tested source `da24aa63188e850df9c9bc25bd9b738b738a3bcd` on Windows 11 AMD64, Python 3.14.3. Runtime-only setup and real samples completed before dev installation. Windows suite: 133 run, 130 passed, 3 skipped, no failures/errors; strict exits 1. Direct-browser checks: 19 passed with actual downloads. Network-disabled Linux container on this PC: 133 tests, no skips, 19 browser checks.

Windows manifest and browser synchronization checks were repaired with retained regressions. Evidence is ignored under `artifacts/local-qa/20260907-acceptance-01/`. Historical release reports remain historical. Native-session and symlink limits are detailed in the report.
