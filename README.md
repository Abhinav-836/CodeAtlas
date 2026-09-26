# 🚀 CodeAtlas – AI-Powered Code Intelligence Platform

Transforming repositories into intelligent, AI-assisted analysis reports.

CodeAtlas is a full-stack platform that lets developers upload a
repository (via GitHub, ZIP, or a local path) and get back a structured
analysis — security findings, code metrics, architecture layout, and an
LLM-generated summary — through a clean web UI.

---

## 🌟 Why CodeAtlas?

- 🔒 **Security scanning** — hardcoded secrets (including ones committed
  and later removed from git history) and common vulnerability patterns
- 📊 **Code metrics** — file counts, LOC, language mix, complexity, and a
  composite risk score
- 🏗️ **Architecture overview** — groups files into layers by convention
- 🤖 **AI-generated insights** — an executive summary and per-file
  explanations via a local or cloud LLM
- ⚡ **Fast, async analysis** — upload, watch live progress, get a report

---

## 🏗️ Architecture

```
CodeAtlas/
│
├── backend/     → FastAPI / Python analysis engine
├── frontend/    → React + Vite UI
│
└── AI Layer     → Ollama (local or cloud), auth-aware
```

### Backend
- Python, FastAPI, SQLAlchemy (async)
- Ollama integration for AI summaries (local models or Ollama Cloud)
- Secrets + vulnerability scanning, metrics, architecture inference
- Async task queue for background analysis

### Frontend
- React
- Vite
- Tailwind CSS
- Live analysis progress, results dashboard, reports list

---

## 🧠 Core Features

- 📁 Repository ingestion — GitHub clone, ZIP upload, or local path
- 🔒 Secrets & vulnerability scanning (Python AST-based + regex for
  other languages)
- 📊 Metrics, complexity, and a risk score
- 🤖 AI-powered executive summary and per-file "explain this" endpoint
- 📄 Export as JSON, Markdown, HTML, or PDF
- 🖥️ CLI (`codeatlas analyze` / `codeatlas export`)

> **Not yet implemented** (despite sometimes being mentioned in early
> planning docs): semantic/embedding-based code search, and an
> OpenRouter fallback. Today the only LLM backend wired in is Ollama —
> local or cloud, with `OLLAMA_API_KEY` sent automatically for cloud
> models.

---

## 🛠️ Tech Stack

**Frontend**: React, Vite, Tailwind CSS

**Backend**: Python, FastAPI, Uvicorn, SQLAlchemy (async, SQLite/Postgres)

**AI**: Ollama (local or cloud)

---

## 🚀 Getting Started

### 1️⃣ Clone the repository

```bash
git clone https://github.com/Abhinav-836/CodeAtlas.git
cd CodeAtlas
```

### 2️⃣ Backend setup

```bash
cd backend
python -m venv venv

# macOS/Linux
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env   # edit as needed

uvicorn app.main:app --reload
```

Backend runs on: `http://127.0.0.1:8000`
Interactive docs: `http://127.0.0.1:8000/docs` (when `DEBUG=True`)

### 3️⃣ Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on: `http://localhost:5173`

Set `VITE_API_URL` in the frontend's environment to point at the
backend when deploying — without it, the app falls back to
`http://localhost:8000`, which only works locally.

### 4️⃣ Local LLM (optional)

```bash
ollama run gpt-oss:20b
```

Point `OLLAMA_BASE_URL` and `LLM_MODEL` at your instance in `.env`. For
an Ollama Cloud model, also set `OLLAMA_API_KEY`.

---

## 🔐 Auth

An `X-API-Key` dependency exists in `app/api/dependencies.py` but is
**not currently applied to any route** — the API is open by default.
Set a real `API_KEY` and add `dependencies=[Depends(get_api_key)]` to
routes you want to lock down before deploying publicly.

---

## 🤝 Contributing

Contributions welcome — fork the repo and open a pull request.

## 📄 License

MIT

## 👨‍💻 Author

**Abhinav Ashutosh**