# CodeAtlas API Documentation

Base URL (local): `http://localhost:8000`

**Auth note:** `app/api/dependencies.py` has an `X-API-Key` header
dependency implemented, but it is **not currently applied to any
route** — every endpoint below is open. If you re-enable it on a
route, that endpoint will require the header `X-API-Key: <API_KEY>`.

---

## Health (`/health`)

### `GET /health`
Liveness check with basic system info (uptime, and CPU/memory/disk
stats if `psutil` is installed).

**Response**
```json
{
  "status": "healthy",
  "service": "CodeAtlas",
  "timestamp": "2026-01-01T00:00:00Z",
  "version": "1.0.0",
  "uptime": "2h 14m 3s"
}
```

### `GET /health/detailed`
Same as above plus process-level metrics (PID, thread count, per-process CPU/memory).

### `GET /health/ready`
Readiness probe — returns `ready` / `not_ready`.

### `GET /health/live`
Liveness probe — always returns `alive` if the process is running.

---

## Upload (`/api/upload`)

### `POST /api/upload/zip`
Multipart upload of a `.zip` file (max 100 MB). Extracts to
`storage/uploads/<name>_<uuid>/`.

**Returns**: `{ success, filename, extracted_to, file_count, message }`

### `POST /api/upload/github`
Clone a GitHub repository (shallow, `--depth 1`).

**Query params**: `repo_url` (required), `branch` (optional — if
omitted, uses the repo's default branch)

**Returns**: `{ success, repo_url, normalized_url, repo_name, branch, local_path, size_kb, duration_seconds, file_count, message }`

### `GET /api/upload/uploads`
List extracted ZIP uploads currently on disk.

### `DELETE /api/upload/uploads/{name}`
Delete an upload directory by name.

---

## Analyze (`/api/analyze`)

### `POST /api/analyze`
Start an analysis task in the background.

**Query params**
- `path` (required) — absolute path to the repo on disk (from a prior
  upload/clone, or any local path the server can read)
- `options` (optional, JSON body) — `include_security`,
  `include_complexity`, `generate_docs`, `depth` (`quick`/`standard`/`full`)

**Returns**
```json
{
  "success": true,
  "analysis_id": "…uuid…",
  "task_id": "…uuid…",
  "status": "queued",
  "check_status_url": "/api/analyze/status/<task_id>",
  "get_results_url": "/api/analyze/results/<task_id>",
  "estimated_time": 45
}
```

### `GET /api/analyze/status/{task_id}`
Poll task status (`queued` / `running` / `completed` / `failed` / `timeout` / `cancelled`).

### `GET /api/analyze/results/{task_id}?include_ai=true`
Fetch the final report once the task is complete. Returns `425` if
still processing. `include_ai=true` adds an LLM-generated summary
(`ai_insights`) to the response.

### `GET /api/analyze/queue/stats`
Queue-wide counters: total tasks, status breakdown, worker availability.

### `GET /api/analyze/recent?limit=10`
Most recently created tasks.

---

## Reports (`/api/reports`)

All reports are stored as JSON files under `storage/reports/` (not in
the database yet — see `architecture.md`).

### `GET /api/reports?limit=&offset=&sort=&order=`
List saved reports. `sort`: `created` | `modified` | `size` | `name`.

### `GET /api/reports/search?query=&risk_level=&min_score=&max_score=&date_from=&date_to=`
Search reports by filename/path/content and filter by risk score or date range.

### `GET /api/reports/{report_id}?format=json|html|markdown|pdf&download=true|false`
Fetch a report rendered in the requested format.

### `GET /api/reports/{report_id}/preview`
First ~10 KB of the raw report file, for a quick peek.

### `GET /api/reports/{report_id}/metadata`
File-level metadata (size, created/modified timestamps, status).

### `GET /api/reports/{report_id}/summary`
Curated summary metrics (risk, secrets/vuln counts, complexity, etc.) —
this is what the frontend's report list and detail views actually use.

### `DELETE /api/reports/{report_id}`
Delete a report file.

### `POST /api/reports/{report_id}/export?format=…`
Materialize a report as a downloadable file under `storage/exports/`
and return a `download_url`. Prefer `GET /api/reports/{id}?format=…&download=true`
for a direct one-shot download instead — it doesn't leave a temp file
on disk.

### `GET /api/reports/download/{filename}`
Download a previously exported file by name.

### `POST /api/reports/save`
Save an externally-produced report dict directly (bypasses the analyze pipeline).

### `DELETE /api/reports/exports/cleanup?older_than_days=7`
Purge old export files.

---

## AI (`/api/ai`)

### `POST /api/ai/explain`
Explain a single file in plain English.

**Query params**: `file_path`, `code` (the actual file contents — this
is what gets sent to the LLM), `language` (optional)

### `POST /api/ai/ask`
Free-form Q&A, optionally with `context` (e.g. relevant code snippets).

**Query params**: `question`, `context` (optional)

### `WS /api/ai/chat`
Streaming chat. Send `{"question": "...", "context": "..."}` as JSON.
Receives `ack` → one or more `chunk` events → `complete` (or `error`).

### `GET /api/ai/models`
List models available on the connected Ollama instance.

### `POST /api/ai/models/switch?model_name=…`
Switch the active model for subsequent calls.

### `GET /api/ai/status`
AI feature flags (`ENABLE_AI_SUMMARIES`/`README`/`INSIGHTS`) plus
whether Ollama is currently reachable.

**Auth note for cloud models**: if `OLLAMA_MODEL` points at an Ollama
Cloud model (a `-cloud` suffix), set `OLLAMA_API_KEY` — it's sent as
`Authorization: Bearer <key>` automatically on every request.

---

## WebSockets

### `WS /ws/status/{task_id}`
Pushes task-status updates every 2 seconds until the task reaches a
terminal state (`completed`/`failed`/`cancelled`).

### `WS /ws/notifications`
Heartbeat channel. Send `"ping"`, receive `{"type": "pong", ...}`; also
emits periodic `{"type": "heartbeat", ...}` messages on its own.

---

## Error format

```json
{ "detail": "human-readable message" }
```

Validation errors (`422`) additionally include an `errors` array with
per-field details.