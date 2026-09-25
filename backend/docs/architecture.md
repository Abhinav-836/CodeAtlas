# CodeAtlas Architecture

This document describes the components that actually exist in the
codebase today — not aspirational infrastructure. Where something is
planned but not built, it's called out explicitly rather than implied.

## Request Flow

```
Client (React frontend, or CLI, or curl)
        │
        ▼
FastAPI app (backend/main.py)
        │
        ├─ Middleware: CORS, GZip, request logging
        ├─ Exception handlers: validation, HTTP, generic
        │
        ▼
Routers (app/api/routes/)
        ├─ /health          — liveness/readiness probes
        ├─ /api/upload      — ZIP + GitHub ingestion
        ├─ /api/analyze     — enqueue + poll analysis tasks
        ├─ /api/reports     — list/search/export saved reports
        └─ /api/ai          — explain / ask / chat / model status
        │
        ▼
Services (app/services/)
        ├─ ingestion/  — file_scanner, repo_loader, zip_loader, ignore_rules
        ├─ analysis/   — metrics, architecture, ast_parser, dependency_graph, flow_extractor
        ├─ security/   — secrets_scanner, vuln_patterns, license_checker
        ├─ export/     — json, html, markdown, pdf
        └─ ai/         — llm_client (Ollama), summarizer, analyze_ai
        │
        ▼
Workers (app/workers/)
        ├─ task_queue.py    — in-process async queue with a thread pool
        └─ analyze_task.py  — orchestrates one full repo analysis
        │
        ▼
Storage
        ├─ storage/uploads  — extracted ZIPs
        ├─ storage/repos    — cloned git repos
        ├─ storage/reports  — analysis results, as JSON files
        └─ storage/exports  — user-requested export files
```

## Core Components

### Ingestion
- **ZIP upload** — path-traversal-safe extraction, 100 MB limit.
- **GitHub clone** — `git clone --depth 1`, HTTPS or SSH URLs, several
  URL formats accepted (`user/repo`, full URL, `.git` suffix, etc.).
- **Local path** — recursive scan with ignore rules (`.git`,
  `node_modules`, `__pycache__`, and similar are skipped by default).

### Analysis Engine
- **Metrics** — file counts, sizes, language mix, a composite risk
  score, and Python AST-derived complexity (functions/classes/imports
  per file, most-complex-files ranking).
- **Architecture inference** — groups files into layers by path
  convention (`/api/`, `/services/`, `/db/`, `/utils/`, everything
  else falls into `other`). This is a simple convention match, not
  static analysis of actual coupling.
- **Dependency graph** (`dependency_graph.py`, `flow_extractor.py`) —
  builds an import/call graph with `networkx`, can detect circular
  dependencies and suggest refactoring targets. Present in the
  codebase but not yet called from the main analysis pipeline.

### Security Scanner
- **Secrets** — regex patterns for common key shapes, a Shannon-entropy
  pass for unlabeled high-randomness strings, and a git-history walk
  (up to 200 commits) so a secret that was committed and later removed
  is still caught. Minified/vendored files (`.min.js`, `node_modules/`,
  `dist/`, etc.) are skipped to cut false positives.
- **Vulnerability patterns** — Python files are parsed with `ast` so
  only real `Call` nodes on genuinely dangerous names are flagged
  (`eval(...)`, `pickle.loads(...)`, `os.system(...)`), not lookalikes
  like `re.compile(...)`. Other languages use a small set of
  conservative regex patterns (`shell=True`, `verify=False`, hardcoded
  key shapes). This is pattern matching, not dataflow analysis — it
  flags leads, not confirmed exploits.
- **License checking** (`license_checker.py`) — detects a repo's
  license file and flags known-incompatible dependency licenses.
  Implemented but not yet wired into a route.

### AI Layer
- **LLM client** (`llm_client.py`) — talks to Ollama's `/api/chat`
  (sync, async, and streaming). Sends `Authorization: Bearer <key>`
  when `OLLAMA_API_KEY` is set, for Ollama Cloud models. Falls back to
  a canned response if the model is unreachable, so the rest of an
  analysis still completes.
- **Endpoints** — `/api/ai/explain` (per-file explanation),
  `/api/ai/ask` (free-form Q&A), `/api/ai/chat` (streaming WebSocket),
  `/api/ai/models`, `/api/ai/status`.
- **Embeddings** (`embeddings.py`) — supports OpenAI, a local hash-based
  fallback, and a random "fake" backend for testing. Implemented but
  not currently called from any route.

### Export Layer
- **JSON** — the canonical format; every report is stored this way.
- **Markdown / HTML** — human-readable renderings of the same data.
- **PDF** — via `reportlab`; degrades gracefully (returns `None`,
  surfaced as a 500 with a clear message) if `reportlab` isn't
  installed.

### Storage Layer
- **Filesystem** is the source of truth today: uploads, cloned repos,
  and JSON reports all live under `storage/`.
- **Database** (`app/db/`) — SQLAlchemy models exist (`User`,
  `Analysis`, `Report`, `Finding`, `Export`, etc.) and the async
  session layer works against SQLite (`aiosqlite`) or PostgreSQL
  (`asyncpg`), but no route currently reads or writes through it. It's
  scaffolding for a future move off flat JSON files.

## Task Queue

`task_queue.py` is an in-process queue: a `ThreadPoolExecutor` plus an
asyncio-friendly `enqueue()`/`get_status()`/`get_result()` interface.
It persists task results to `storage/task_results/` as a recovery
mechanism, but the live callable reference is what's actually used to
run a task — persistence is only a fallback path for a task rehydrated
after a restart. It is **not** distributed; if you need multiple
worker processes, this would need to be swapped for something like
Celery or Arq. Nothing in the current code assumes that swap has
happened, so this document doesn't describe one.

## Security Notes

- API-key authentication exists (`app/api/dependencies.py`,
  constant-time comparison) but is **not currently applied to any
  route** — see the README for how to turn it on.
- Path-traversal guards are in place on ZIP extraction and on the
  exported-file download endpoint.
- CORS origins are configured via `CORS_ORIGINS` in settings; there is
  no separate API gateway or load balancer — a single FastAPI process
  handles everything.

## Deployment (current)

Both the FastAPI backend and the React frontend are deployed on
Render, as two separate services, with auto-deploy on push. There is
no Redis, no message queue, no S3-compatible storage, and no
Kubernetes — those aren't part of this project's current
infrastructure.