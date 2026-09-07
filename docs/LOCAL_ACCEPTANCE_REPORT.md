# RecoveryLab: current local acceptance report

Status: BLOCKED. Required Windows permissions/session gates remain. This is not full local acceptance.

Run date: 2026-09-08, Asia/Karachi.
Tested current main commit: `f023eb7b63cc4508980143cd062f2f2bd1d53949`.
Starting state: main, clean, correct danial-maqbool origin. Fetch and fast-forward pull completed without discarding changes.
Working source diff at test time: empty; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
Environment: Windows 11 Home build 26200, AMD64; project-local Python 3.14.3. Tesseract 5.4.0.20240606 with eng/osd; Poppler pdftoppm 26.07.0. Browser engine 143.0.7499.4.
Current evidence root: ignored `artifacts/local-qa/20260908-final-acceptance-01/`.
Earlier evidence root: ignored `artifacts/local-qa/20260907-acceptance-01/`.
The [previous acceptance report](history/LOCAL_ACCEPTANCE_20260907.md) is preserved verbatim. Earlier failures and blocked checks remain historical evidence.

## Current and retained checks

| Gate | Status | Executions and evidence |
| :--- | :--- | :--- |
| Starting Git state | PASS | `starting-state.json`, `fetch-pull.log`, `tested-source.txt`; main only is the final branch policy. |
| Windows source/vault symlinks | BLOCKED | Fresh disposable-directory creation probe returns WinError 1314. Exact existing tests: 2 run, 0 passed, 2 skipped, 0 failures/errors. `windows-symlinks/result.json`, `windows-symlinks/tests.log`. |
| Windows POSIX ciphertext mode | NOT APPLICABLE | POSIX mode assertions do not apply to Windows. It is not an application failure. |
| Full regression suite | PASS | Retained 2026-09-07 evidence: 133 executions, 130 passed, 0 failures/errors, 3 skipped. Prior `--strict` exited 1 because of skips; no fresh full-suite claim. Earlier `final-suite/test-report.json`. |
| Browser | PASS | Retained 2026-09-07 direct-browser evidence: 19 checks. Earlier `final-browser/browser-report.json`; not rerun. |
| Runtime unchanged | PASS | Compared current main with previously tested source `da24aa63188e850df9c9bc25bd9b738b738a3bcd`. Only report/handoff/manifest files differ. `changes-since-tested-source.txt`. No reason to repeat installation or complete feature suites. |

## Project acceptance cases

PASS cases carried from the previous report remain supported by their original dated evidence. Native blockers were reassessed this run.

| Case | Status | Findings | Evidence |
| :--- | :--- | :--- | :--- |
| RL-01 | PASS | Five sample batch copies finish; real downloads/reports match backend bytes; signatures and hex view checked. | Earlier report/evidence: `final-browser; final-acceptance/results.json` |
| RL-02 | PASS | JSON/JSONL, malformed records, CSV quoting/ragged rows/formula escaping and legacy encoding; unsupported repairs rejected. | Earlier report/evidence: `final-suite/verify.log` |
| RL-03 | PASS | Missing directory, truncated entry, CRC, unsafe/encrypted entries and expansion; omissions verified. Nested ZIP stays byte-identical without recursive extraction. | Earlier report/evidence: `final-suite; supplemental-archives/results.json` |
| RL-04 | PASS | DOCX/XLSX/PPTX opened and rendered by Microsoft Office 16; PDF independently rendered. Values preserved. Default spreadsheet column width clips text visually; logical cell remains intact. | Earlier report/evidence: `extended-02/office-independent-render; final-acceptance` |
| RL-05 | PASS | PNG/JPEG/GIF pixels independently decoded by Chromium; missing/invalid pixel data rejected. | Earlier report/evidence: `final-acceptance/results.json; final-suite` |
| RL-06 | PASS | SQLite integrity, table/BLOB bytes, source hashes and Windows handle cleanup. | Earlier report/evidence: `final-acceptance/results.json` |
| RL-07 | PASS | FFmpeg remux, streams/duration, frame decode and Chromium playback: one second, 160x120, ten decoded frames. Network input/playlist rejection tested. | Earlier report/evidence: `final-acceptance; extended-02/video-playback.json; final-suite` |
| RL-08 | PASS | Cancellation, occupied names, malformed inputs and failed workers. Windows ACL-denied export fails without output or changed sources; test ACL restored. | Earlier report/evidence: `final-interaction; final-suite; readonly-destination-03/result.json` |

## Defects, regression tests and verification scope

No application defect required a source-code change during this run. No application regression test was added by this run. No assertion, encryption, consent, source protection or parser limit was weakened. No shared localdesk file changed.

## Native Windows blockers

The user explicitly confirmed that no disposable Windows session is available. No login task, credential-store write, desktop input or window-title capture was attempted on the personal session. Process-restart evidence from the earlier run is not logout/login evidence.
A fresh symlink probe ran only inside disposable synthetic directories. Windows returned error 1314, a required privilege is not held. Both existing source/vault tests were invoked; their skips remain BLOCKED, not PASS. No machine-wide security configuration was changed.

## Commands and evidence

Exact command arguments, start times, exits and durations are in `*.command.json`; native/interpreter versions are in `environment.log`. Raw paths, logs, vaults and synthetic outputs stay ignored. No personal documents, browser databases, credentials or screenshots were used. Only owned test processes were stopped.

Source-manifest verification follows review of report-only changes and is recorded in `final-manifest.log`. Runtime-only installation and prior offline runs are retained evidence and were not repeated. No new network-isolation result is claimed for this run.

GitHub final main workflow results are recorded after the report push in the workspace five-project summary and ignored `final-ci.json`; remote CI does not replace local Windows permissions. No queued or running job is called a pass.

## Exact remaining user actions

1. Supply a disposable Windows environment with symbolic-link creation capability, then run the existing source and vault symlink rejection tests there. No global security setting was changed to obtain that capability.

## Decision

Overall: BLOCKED by the native Windows capability/session requirements listed above. Other accepted project behavior retains its previous evidence; no new full acceptance claim is made.
