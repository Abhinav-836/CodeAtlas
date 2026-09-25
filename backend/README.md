# CodeAtlas 🚀

**CodeAtlas** is an AI-powered code intelligence platform. Point it at a
GitHub repo, a ZIP file, or a local path, and it scans the codebase for
secrets, common vulnerability patterns, and code metrics — then uses an
LLM (via [Ollama](https://ollama.com), local or cloud) to generate a
plain-English summary of what it found.

---

## ✨ Features

- 🔍 **Repository ingestion** — GitHub clone, ZIP upload, or a local path
- 🔒 **Security scanning**
  - Secrets: known token shapes (AWS, Stripe, etc.), key=value patterns,
    high-entropy strings, and secrets committed then later removed
    (full git history is scanned, not just the current files)
  - Vulnerabilities: Python files are parsed with `ast` for real Call
    nodes (`eval`, `pickle.loads`, `os.system`, etc.); other languages
    use conservative regex patterns
- 📊 **Metrics** — file counts, lines of code, language mix, a risk score,
  and Python-specific complexity (functions/classes/imports per file)
- 🏗️ **Architecture inference** — groups files into layers by path
  convention (`/api/`, `/services/`, `/db/`, `/utils/`)
- 🤖 **AI insights** — an LLM-generated executive summary per analysis,
  plus a per-file "explain this" endpoint
- 📄 **Export** — JSON, Markdown, HTML, and PDF (PDF requires `reportlab`)
- ⚡ **Async task queue** — analysis runs in the background; poll for
  status or fetch results once complete
- 🖥️ **CLI** — `codeatlas analyze` / `codeatlas export` talk to the same
  running API

---

## 🏗️ Project Layout

```
CodeAtlas/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── app/
│   │   ├── api/
│   │   │   ├── dependencies.py  # API-key auth helper (not currently applied)
│   │   │   └── routes/          # health, upload, analyze, reports, ai
│   │   ├── core/                # config.py (settings), security.py
│   │   ├── db/                  # SQLAlchemy models + sessions (not yet wired to routes)
│   │   ├── services/
│   │   │   ├── ai/              # llm_client, summarizer, analyze_ai
│   │   │   ├── analysis/        # metrics, architecture, ast_parser, dependency_graph, flow_extractor
│   │   │   ├── export/          # json, html, markdown, pdf
│   │   │   ├── ingestion/       # file_scanner, repo_loader, zip_loader, ignore_rules
│   │   │   └── security/        # secrets_scanner, vuln_patterns, license_checker
│   │   ├── utils/                # ignore_matcher, file_utils, hash_utils, language_map, timer
│   │   └── workers/              # analyze_task.py, task_queue.py
│   ├── cli/
│   │   ├── maincli.py
│   │   └── commands/             # analyze.py, export.py
│   ├── scripts/
│   │   ├── seed_db.py
│   │   └── cleanup_temp.py
│   ├── storage/                  # uploads, repos, reports, exports (created at runtime)
│   └── requirements.txt
└── frontend/                     # React + Vite + Tailwind UI
    └── src/
```

---

## 🚀 Getting Started

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # edit as needed
uvicorn app.main:app --reload
```

Interactive docs: `http://localhost:8000/docs` (when `DEBUG=True`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` in the frontend's environment to point at the
backend — without it, the built app falls back to
`http://localhost:8000`, which only works locally.

### Local LLM (optional)

```bash
ollama run gpt-oss:20b
```

Point `OLLAMA_BASE_URL` and `LLM_MODEL` at your instance in `.env`. For
Ollama Cloud models, also set `OLLAMA_API_KEY` — it's sent as a Bearer
token automatically.

If no LLM is reachable, AI-powered endpoints degrade to a canned
fallback message rather than failing outright.

---

## 🔐 Auth

`app/api/dependencies.py` has an `X-API-Key` dependency, but it is
**not currently applied to any route** — the API is intentionally open
right now. To lock down mutating endpoints, add
`dependencies=[Depends(get_api_key)]` to the relevant route decorators
and set a real `API_KEY` in your environment.

---

## 🧠 Tech Stack

- **Backend**: FastAPI, SQLAlchemy (async), Python 3.10+
- **Frontend**: React, Vite, Tailwind CSS
- **AI**: Ollama (local or cloud), with an OpenAI-compatible fallback
  path in `embeddings.py` (not currently wired into the API)
- **Deployment**: Render (both services, this project's current setup)

---

## 📌 Known Limitations

- GitHub imports are cloned with `--depth 1` (shallow), so git-history
  secret scanning only finds anything on locally-pointed paths with
  full history, not on freshly-cloned GitHub repos.
- The database layer (`app/db/`) exists but isn't wired into any live
  route yet — reports are stored as JSON files on disk, not in the DB.
- Vulnerability scanning flags *leads*, not confirmed issues — it has
  no dataflow analysis, so `eval(literal)` and `eval(user_input)` look
  identical to it.

---

## 🤝 Contributing

Contributions are welcome — fork the repo and submit a pull request.

## 📄 License

MIT.

## 👨‍💻 Author

**Abhinav Ashutosh**