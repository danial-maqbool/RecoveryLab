# Daily use

## Start

Install Python 3.11 or later. Open the extracted project folder. Run `python bootstrap.py` once, then use `start.bat` on Windows or `sh start.sh` on Linux or macOS. Setup creates a private `.venv` folder. See [Setup](SETUP.md) for local tools and offline installation.

The normal app asks for a vault passphrase with at least 12 characters. Keep that passphrase. No server can reset it. Use `start.bat --demo` or `sh start.sh --demo` to try synthetic data without a persistent database.

The browser connects only to the local Python process. Closing the browser does not stop the worker. Press Ctrl+C in the terminal to stop a foreground worker. Use `run.py --port 0` to select a free port.

## Inspect and recover

Select **Use sample files**. Open the damaged JSON sample. Read the problem and proposed changes. Create a recovered copy. Open the new file and its report. Select the missing-directory ZIP example to compare a different recovery method.

For your own files, drop a file onto the workbench or select a local path. Read the signature, hash, structure checks, and coverage notes. A structure check does not prove that all content is correct. Use the read-only hex view to examine the first bytes.

| Input | Recovery behavior |
| :--- | :--- |
| JSON | Remove supported comments or trailing commas, then parse and serialize the result. No arbitrary code is evaluated. |
| JSONL | Keep complete valid JSON lines. Report excluded line numbers. |
| CSV or encoded text | Normalize readable text and delimiters. Report the changes. |
| ZIP | Rebuild verified stored or deflated entries from surviving headers. Reject unsafe paths and unsupported entries. |
| PDF | Rebuild pages that the local parser can read. Reject password-protected input. Verify the new page structure. |
| DOCX, XLSX, PPTX | Recover surviving ZIP entries. Return an Office file only when the required package parts pass validation. Otherwise return a recovery ZIP. |
| PNG, JPEG, GIF | Re-encode pixels that the decoder can read. Animated input uses the first frame and reports that loss. |
| SQLite | Copy an intact database. For readable parts of damaged databases, attempt bounded table recovery and report schema losses. |
| gzip | Expand a valid bounded stream into a new file. Check its integrity. |
| MP4 or Matroska | Use local FFmpeg to remux readable audio and video streams into a new Matroska file. |

FFmpeg and ffprobe must be installed for video processing. The video path does not fetch remote streams. It does not recreate missing frames. PDF and Office recovery are not privacy sanitization. Recovered documents can still contain links, attachments, or private information.

## Check the result

Use the output list to download the recovered file and its report. Compare important pages, rows, images, or durations with a trusted copy. Inspect batch results separately. A successful repair applies only to the reported failure case. It does not certify that every source byte survived.

## Storage and support

The app stores its database in `.local-data/app.vault`. The database and its backups use authenticated encryption. Uploaded source copies and exported files are not encrypted by this app. Keep them in a protected folder.

Stop the app before copying its whole data folder. Keep the passphrase with a separate protected backup. Do not delete an original file until you have checked its output. Deleting a folder is not secure disk erasure.

When a source changes after review, scan it again. When a parser reports a size, page, or time limit, split the source. Do not publish private examples in a bug report. Include the exact error, app version, operating system, and a synthetic sample instead.
