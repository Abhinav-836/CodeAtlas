# CodeAtlas Roadmap

This tracks what's actually built vs. what's planned. No fabricated
star counts or user metrics — those were placeholders from an earlier
draft and didn't reflect anything real.

## ✅ Built and working

- Repository ingestion: GitHub clone, ZIP upload, local path
- Async task queue for background analysis
- Metrics: file counts, LOC, language mix, risk score, Python
  complexity
- Architecture inference by path convention
- Security scanning: secrets (regex + entropy + git history),
  Python-AST-based vulnerability patterns, regex patterns for other
  languages
- AI layer: Ollama integration (local + cloud, with auth), executive
  summaries, per-file explanations, streaming chat
- Export: JSON, Markdown, HTML, PDF
- CLI (`codeatlas analyze`, `codeatlas export`)
- React frontend: upload flow, live analysis progress, results
  dashboard, reports list
- Deployed on Render (backend + frontend as separate services)

## 🚧 Scaffolded but not wired in

- **Database layer** (`app/db/`) — models and async sessions exist;
  reports are still stored as flat JSON files, not read from the DB.
- **API-key auth** (`app/api/dependencies.py`) — implemented, not
  applied to any route yet.
- **Dependency graph analysis** (`dependency_graph.py`,
  `flow_extractor.py`) — builds real call/import graphs with
  `networkx`, not yet called from the main analysis pipeline.
- **License checking** (`license_checker.py`) — detects licenses and
  flags incompatible dependencies, not yet exposed via an endpoint.
- **Embeddings** (`embeddings.py`) — OpenAI/local/fake backends
  implemented, not called from anywhere yet.

## 🔜 Not started

- Multi-language complexity analysis beyond Python (JS/TS AST parsing)
- Real cyclomatic complexity (current Python complexity score is a
  simple function/class/import count, not McCabe complexity)
- Dependency vulnerability scanning against a real CVE database
  (e.g. OSV.dev)
- CI baseline mode (report only *new* findings vs. a saved baseline)
- Git-history intelligence beyond secrets (hotspots, bus factor,
  orphaned-file detection)
- User accounts / multi-tenant reports (depends on the DB layer above
  actually being wired in)

## Known limitations to design around, not just fix later

- GitHub imports are shallow-cloned (`--depth 1`), so git-history
  secret scanning only works on repos with full local history, not on
  fresh GitHub clones, unless the clone depth is changed.
- The task queue is in-process and single-instance — it does not
  survive a process restart mid-task, and does not scale across
  multiple server instances without a real message broker.
- Vulnerability findings are pattern matches, not proven exploits —
  there's no dataflow tracking between input sources and dangerous
  sinks.

## How to contribute

- Found a bug? Open an issue with repro steps.
- Want to pick up one of the "scaffolded but not wired in" items?
  Those are the most valuable next steps — the hard part (the code)
  already exists, it just needs a route/caller.