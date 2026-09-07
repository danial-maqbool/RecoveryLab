# Local API

This API is for the running local app. It is not a hosted service or a stable public API contract.
The server listens on `127.0.0.1:8763` by default.

## Session checks

The index page supplies a random token for the current Python process.
The UI sends it in the `X-Local-Token` header. Every API request must use the current token.
POST requests must use `Content-Type: application/json`. The body limit is 36 MiB.
The server checks Host and Origin and does not enable cross-origin access.

Do not copy the token into a repository or enable network forwarding to the port.
Restarting the Python process changes the token.

## Common operations

| Method | Path | Input | Result |
| :--- | :--- | :--- | :--- |
| GET | `/api/info` | none | Name, version, paths, and local optional-tool availability. |
| GET | `/api/state` | none | Current application state and recent jobs. |
| GET | `/api/browse` | path, optional | Up to 1,500 visible folder entries. |
| GET | `/api/jobs/ID` | job ID in the path | Status, progress, result, or error. |
| POST | `/api/cancel` | id | Request cooperative job cancellation. |
| POST | `/api/upload` | name, base64 content | Save a new private inbox file. |
| POST | `/api/backup` | none | Write a database-only backup artifact. |

## Application operations

| Method | Path | Input | Result |
| :--- | :--- | :--- | :--- |
| GET | `/api/inspection` | id | Return one complete inspection. |
| GET | `/api/hex` | id; offset, optional | Return a bounded byte view. |
| GET | `/api/examples` | none | List bundled synthetic input paths. |
| POST | `/api/inspect` | paths, or path | Inspect 1 to 20 files in a job. |
| POST | `/api/repair` | id | Start an available copy-only recovery method. |
| POST | `/api/export` | id | Write an inspection JSON report. |

### Example request body

Send this JSON to `POST /api/inspect` with the current session token:

```json
{
  "paths": [
    "C:/Users/You/Documents/broken.json"
  ]
}
```

Use paths from the computer running Python. Change the example path before sending the request.
A job-start response contains `job_id`. Read `/api/jobs/ID` until its status is terminal.
Read the error field when the job fails. Do not treat a queued response as a completed operation.

An artifact response contains its name, relative output path, and size. The browser download helper requests only paths under the app output directory.
Use `web/common.js` as the reference client for the exact response envelope and download route.

## Version 0.2.0

All routes require the local session token. Use the user interface to review a job before an output operation. The source hash binds a review to the selected source bytes.

Existing inspect and recovery routes now support the native methods listed in the user guide. Recovery results include verified output format, source hash, and explicit loss notes.
