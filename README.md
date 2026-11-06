# CodeAtlas

Point CodeAtlas at a GitHub repo or a ZIP of your project and get a report back: leaked secrets (including ones deleted from git history), common vulnerability patterns, code metrics and complexity, language breakdown, an overall risk score, and an AI-written summary of what the codebase does.

**Live:** [code-atlas-nine.vercel.app](https://code-atlas-nine.vercel.app)

| | |
|---|---|
| **Frontend** | Next.js 16 (App Router), React 19, Tailwind CSS 4 — deployed on Vercel |
| **Backend** | Python, FastAPI, async SQLAlchemy, background task queue — deployed on Render |
| **AI** | Ollama, local or Ollama Cloud (default model `gpt-oss:120b-cloud`) |

## How it works

```
GitHub URL or .zip
  ─► clone / extract into the uploader's own folder (ignore rules skip node_modules, venv, build output…)
  ─► background task:
       secrets scan ─ working tree + last 200 commits of git history
       vulnerability patterns ─ AST for Python, regex for other languages
       complexity ─ Python AST, tree-sitter for JavaScript / TypeScript
       metrics ─ files, lines, functions, classes, complexity, languages
       architecture ─ groups files into layers by convention
       AI summary ─ Ollama
  ─► overall risk score ─► report saved ─► download as JSON / Markdown / HTML / PDF
```

The frontend polls the task's status and shows live progress until the report is ready.

**No accounts, but private by default.** Each browser generates a random token on first visit and sends it with every request (`X-Owner-Token`). The server stores only its SHA-256 hash and stamps it on every upload, analysis and report, so people can only see, download and delete their own work. Clearing site data or switching browser starts you fresh.

## Features

- **Two inputs** — a GitHub link (`github.com/owner/repo` or just `owner/repo`) or a `.zip` upload (up to 100 MB)
- **Secrets** — API keys, tokens and passwords in the current files *and* in commits that were later removed
- **Vulnerability patterns** — code execution (`eval`, `exec`, dynamic imports), shell and command injection, insecure deserialisation (Python and PHP), disabled TLS verification, `child_process.exec` in Node
- **Metrics** — files, lines of code, functions, classes, average complexity, language distribution
- **AI summary** — an executive summary of the codebase, plus `explain` / `ask` endpoints for individual files and questions
- **Reports page** — every report you've run, searchable, downloadable in four formats, deletable
- **CLI** — `codeatlas analyze` and `codeatlas export` for running it without the web UI

Not implemented yet: embedding-based semantic code search, and LLM providers other than Ollama.

## Run locally

Needs Python 3.10+ and Node 20+. For AI summaries, either a local [Ollama](https://ollama.com) or an Ollama Cloud API key — the rest of the analysis works without one.

**Backend** (http://localhost:8000, API docs at `/docs`)

```bash
git clone https://github.com/Abhinav-836/CodeAtlas.git
cd CodeAtlas/backend
python -m venv venv
venv\Scripts\activate                # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
CORS_ORIGINS=http://localhost:3000
# Local Ollama:
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=gpt-oss:20b
# Or Ollama Cloud:
# OLLAMA_BASE_URL=https://ollama.com
# OLLAMA_API_KEY=your-key
# LLM_MODEL=gpt-oss:120b-cloud
```

```bash
uvicorn main:app --reload
```

**Frontend** (http://localhost:3000)

```bash
cd CodeAtlas/frontend
npm install
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local
npm run dev
```

**Docker** — `./setup.sh` (or `setup.ps1` on Windows) creates the storage folders and a `.env`, then starts the stack with `docker-compose`.

## Configuration

Read from `backend/.env`.

| Variable | Default | Notes |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | |
| `OLLAMA_API_KEY` | — | Needed for Ollama Cloud models; sent automatically when set |
| `LLM_MODEL` | `gpt-oss:120b-cloud` | Can also be switched at runtime via `POST /api/ai/models/switch` |
| `LLM_TIMEOUT` | `60` | Seconds |
| `ENABLE_AI_SUMMARIES` | `true` | Set `false` to skip the AI step entirely |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | Comma-separated frontend URLs |
| `DATABASE_URL` | `sqlite+aiosqlite:///./codeatlas.db` | |
| `MAX_UPLOAD_SIZE` | `104857600` | Bytes (100 MB) |
| `MAX_WORKERS` / `ANALYSIS_TIMEOUT` | `4` / `300` | Concurrent analyses / seconds per analysis |
| `GITHUB_TOKEN` | — | Optional; raises GitHub rate limits when cloning |
| `CLEANUP_ON_STARTUP` | `true` | Removes leftover temporary clones on boot |
| `DEBUG` | `True` | Set `False` in production |

Frontend: `NEXT_PUBLIC_API_URL` — the backend URL, no trailing slash.

## API

Every route except health needs the `X-Owner-Token` header (32–128 URL-safe characters). Full interactive docs at `/docs`.

| Area | Endpoints |
|---|---|
| Upload | `POST /api/upload/github`, `POST /api/upload/zip`, `GET /api/upload/uploads`, `DELETE /api/upload/uploads/{name}` |
| Analyse | `POST /api/analyze`, `GET /api/analyze/status/{task_id}`, `GET /api/analyze/results/{task_id}`, `GET /api/analyze/recent`, `GET /api/analyze/queue/stats` |
| Reports | `GET /api/reports`, `GET /api/reports/search`, `GET /api/reports/{id}?format=json\|html\|markdown\|pdf`, `GET /api/reports/{id}/summary`, `GET /api/reports/{id}/metadata`, `DELETE /api/reports/{id}` |
| AI | `POST /api/ai/explain`, `POST /api/ai/ask`, `GET /api/ai/models`, `POST /api/ai/models/switch`, `GET /api/ai/status` |
| Health | `GET /health`, `/health/detailed`, `/health/ready`, `/health/live` |

## Project structure

```
backend/
  main.py                FastAPI app
  app/api/routes/        upload, analyze, reports, ai, health
  app/services/
    ingestion/           GitHub clone, ZIP extraction, ignore rules
    security/            secrets (incl. git history), vulnerability patterns, licences
    analysis/            AST parsing, complexity, metrics, architecture, dependency graph
    ai/                  Ollama client, prompts, summariser
    export/              JSON, Markdown, HTML, PDF
  app/core/owner.py      per-browser ownership
  app/workers/           background analysis queue
  cli/                   codeatlas analyze / export
frontend/
  app/                   home (upload), /results/[taskId], /reports
  components/            upload panel, progress, results view, reports browser
  lib/                   API client, owner token, polling hook
```

## Limitations

- Vulnerability detection is pattern-based, not a full static analyser — treat findings as things to look at, not proof of a bug.
- Deep analysis is strongest for Python (AST-based vulnerability checks) and JavaScript/TypeScript (complexity via tree-sitter); other languages get file statistics, regex-based scanning and language metrics.
- Reports are tied to the browser that created them; there's no way to move them to another device yet.
- On Render's free tier, files on disk are cleared on redeploy, so old reports and uploads don't survive a deploy.

---

Built by **Abhinav Ashutosh** · [GitHub](https://github.com/Abhinav-836)