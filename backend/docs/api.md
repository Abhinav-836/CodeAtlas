# CodeAtlas API Documentation

Base URL (local): `http://localhost:8000`

Authentication: endpoints that mutate state require the header `X-API-Key: <API_KEY>`.
Read-only endpoints (health, list reports, list uploads) do not.

---

## Health (`/health`)

### `GET /health`
Liveness check.

**Response**
```json
{ "status": "healthy", "service": "codeatlas-api", "timestamp": 1736000000.0, "version": "1.0.0" }
GET /health/detailed
Detailed health including CPU/memory if psutil is installed.

GET /health/ready
Readiness probe.

GET /health/live
Liveness probe.

Upload (/api/upload)
POST /api/upload/zip 🔒
Multipart upload of a .zip file (max 100 MB). Extracts to storage/uploads/<name>_<uuid>/.

Returns { success, filename, extracted_to, file_count, message }.

POST /api/upload/github 🔒
Clone a GitHub repository.

Query params repo_url, branch (optional).

GET /api/upload/uploads
List extracted uploads.

DELETE /api/upload/uploads/{name} 🔒
Delete an upload directory.

Analyze (/api/analyze)
POST /api/analyze 🔒
Start an analysis task.

Query params

path (required) — absolute path to the repo on disk

options (optional JSON)

Returns

json
{
  "success": true,
  "analysis_id": "…uuid…",
  "task_id": "…uuid…",
  "status": "queued",
  "check_status_url": "/api/analyze/status/<task_id>",
  "get_results_url": "/api/analyze/results/<task_id>",
  "estimated_time": 45
}
GET /api/analyze/status/{task_id}
Poll task status.

GET /api/analyze/results/{task_id}?include_ai=true
Fetch final report. Returns 425 if the task is still running.

GET /api/analyze/queue/stats
Queue-wide counters.

GET /api/analyze/recent?limit=10
Most-recent tasks.

Reports (/api/reports)
GET /api/reports?limit=&offset=&sort=&order=
List reports.

GET /api/reports/search?query=&risk_level=&min_score=&max_score=&date_from=&date_to=
Search reports.

GET /api/reports/{report_id}?format=json|html|markdown|pdf&download=true|false
Fetch a report in the requested format.

GET /api/reports/{report_id}/preview
First ~10 KB of the report.

GET /api/reports/{report_id}/metadata
File metadata for a report.

GET /api/reports/{report_id}/summary
Curated summary metrics.

DELETE /api/reports/{report_id} 🔒
Delete a report file.

POST /api/reports/{report_id}/export?format=… 🔒
Materialise a report as a downloadable file.

GET /api/reports/download/{filename}
Download a previously exported file.

POST /api/reports/save 🔒
Save an externally produced report dict.

DELETE /api/reports/exports/cleanup?older_than_days=7 🔒
Purge old exports.

AI (/api/ai)
POST /api/ai/explain 🔒
Query params file_path, code, language (optional).

POST /api/ai/ask 🔒
Query params question, context (optional).

WS /api/ai/chat
Streaming chat. Send {"question": "...", "context": "..."} JSON. Receives ack / chunk / complete / error events.

GET /api/ai/models
List models available on the Ollama instance.

POST /api/ai/models/switch?model_name=… 🔒
Switch the active model.

GET /api/ai/status
AI feature flags + Ollama connectivity.

WebSockets
WS /ws/status/{task_id}
Push task-status updates every 2 seconds until the task terminates.

WS /ws/notifications
Heartbeat channel. Send ping, receive pong.