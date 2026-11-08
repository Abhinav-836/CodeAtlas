"""
Reports live in the database, not on disk.

Render's free plan wipes the disk on every deploy and restart, so reports
saved as files in storage/reports disappeared each time. They now go in the
database named by DATABASE_URL: SQLite locally, Postgres (e.g. Neon) in
production, where they survive deploys.

Each row keeps:
- the full report as JSON text (what the API serves and exports),
- the headline numbers used by the Reports list, so listing never has to
  parse every report,
- the owner hash (see app/core/owner.py) and, optionally, the hash of a
  read-only share link.

The functions are synchronous on purpose: reports are saved from the
analysis worker threads, and the API calls these through asyncio.to_thread.
"""
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.owner import OWNER_KEY
from app.db.models import Base

logger = logging.getLogger(__name__)


class StoredReport(Base):
    __tablename__ = "stored_reports"

    id = Column(String(64), primary_key=True)
    owner_hash = Column(String(64), index=True, nullable=True)
    share_hash = Column(String(64), unique=True, index=True, nullable=True)
    repo_name = Column(String(255))
    path = Column(Text)
    analysis_id = Column(String(64))
    risk_level = Column(String(20))
    risk_score = Column(Float, default=0)
    files_analyzed = Column(Integer, default=0)
    total_lines = Column(Integer, default=0)
    secrets_found = Column(Integer, default=0)
    vulnerabilities_found = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
    primary_language = Column(String(64))
    size_bytes = Column(Integer, default=0)
    data = Column(Text, nullable=False)  # the full report, JSON
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    shared_at = Column(DateTime(timezone=True), nullable=True)


# ── Engine ───────────────────────────────────────────────────────────

_engine: Optional[Engine] = None
_lock = threading.Lock()


def sync_url(url: str) -> str:
    """The same database as the async app, through a synchronous driver."""
    return url.replace("sqlite+aiosqlite://", "sqlite://")


def engine() -> Engine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                url = sync_url(settings.database_url)
                kwargs: Dict[str, Any] = {"pool_pre_ping": True, "future": True}
                if url.startswith("sqlite"):
                    kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
                else:
                    # Neon's pooled endpoint is PgBouncer, which can't keep prepared statements.
                    kwargs["connect_args"] = {"prepare_threshold": None}
                    kwargs["pool_size"] = 5
                    kwargs["max_overflow"] = 5
                eng = create_engine(url, **kwargs)
                Base.metadata.create_all(eng, tables=[StoredReport.__table__])
                _engine = eng
    return _engine


def reset_engine() -> None:
    """Forget the engine (tests point DATABASE_URL somewhere new)."""
    global _engine
    with _lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None


# ── Helpers ──────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _int(v: Any) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _headline(data: Dict[str, Any]) -> Dict[str, Any]:
    """The numbers the Reports list shows, read from where the analyzer stores them."""
    metrics = data.get("metrics") or {}
    summary = data.get("summary") or {}
    security = data.get("security") or {}
    languages = data.get("languages") or {}
    try:
        score = float(data.get("overall_risk_score", metrics.get("risk_score", 0)) or 0)
    except (TypeError, ValueError):
        score = 0.0
    return {
        "repo_name": (str(data["repo_name"])[:255] if data.get("repo_name") else None),
        "path": str(data.get("path") or "Unknown"),
        "analysis_id": str(data.get("analysis_id") or "")[:64] or None,
        "risk_level": str(data.get("overall_risk_level") or metrics.get("risk") or "unknown")[:20],
        "risk_score": score,
        "files_analyzed": _int(summary.get("files_analyzed", summary.get("total_files", 0))),
        "total_lines": _int(metrics.get("total_lines", 0)),
        "secrets_found": _int(security.get("secrets_found", 0)),
        "vulnerabilities_found": _int(security.get("vulnerabilities_found", 0)),
        "critical_issues": _int((security.get("by_severity") or {}).get("critical", 0)),
        "primary_language": (str(languages["primary_language"])[:64] if languages.get("primary_language") else None),
    }


def _human_size(size: float) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def row_summary(row: StoredReport) -> Dict[str, Any]:
    """What the Reports list and the report summary endpoint return."""
    created = _aware(row.created_at)
    updated = _aware(row.updated_at)
    return {
        "id": row.id,
        "filename": f"{row.id}.json",
        "analysis_id": row.analysis_id or row.id,
        "path": row.path,
        "repo_name": row.repo_name,
        "risk_level": row.risk_level,
        "risk_score": row.risk_score,
        "files_analyzed": row.files_analyzed,
        "total_lines": row.total_lines,
        "secrets_found": row.secrets_found,
        "vulnerabilities_found": row.vulnerabilities_found,
        "critical_issues": row.critical_issues,
        "primary_language": row.primary_language,
        "size_bytes": row.size_bytes,
        "size_kb": row.size_bytes / 1024,
        "size_human": _human_size(row.size_bytes or 0),
        "created": created.isoformat() if created else None,
        "modified": updated.isoformat() if updated else None,
        "shared": row.share_hash is not None,
    }


# ── Reads and writes ─────────────────────────────────────────────────

def save(report_id: str, data: Dict[str, Any]) -> None:
    """Insert or replace a report. Its owner comes from data["_owner"]."""
    body = json.dumps(data, default=str, ensure_ascii=False)
    fields = {**_headline(data), "owner_hash": data.get(OWNER_KEY), "data": body,
              "size_bytes": len(body.encode("utf-8")), "updated_at": _now()}
    with Session(engine()) as db, db.begin():
        row = db.get(StoredReport, report_id)
        if row is None:
            db.add(StoredReport(id=report_id, created_at=_now(), **fields))
        else:
            for k, v in fields.items():
                setattr(row, k, v)


def load(report_id: str) -> Optional[Dict[str, Any]]:
    """The full report (including its owner hash), or None."""
    with Session(engine()) as db:
        row = db.get(StoredReport, report_id)
        if row is None:
            return None
        try:
            data = json.loads(row.data)
        except (TypeError, ValueError):
            return None
        return data if isinstance(data, dict) else None


def get_row(report_id: str) -> Optional[StoredReport]:
    with Session(engine(), expire_on_commit=False) as db:
        return db.get(StoredReport, report_id)


def list_for_owner(owner: str, limit: int = 10000) -> List[Dict[str, Any]]:
    """The owner's reports, newest first. The big JSON column isn't read."""
    cols = [c for c in StoredReport.__table__.columns if c.name != "data"]
    with Session(engine()) as db:
        rows = db.execute(
            select(*cols).where(StoredReport.owner_hash == owner)
            .order_by(StoredReport.created_at.desc()).limit(limit)
        ).all()
    return [row_summary(StoredReport(**r._mapping)) for r in rows]


def delete(report_id: str) -> bool:
    with Session(engine()) as db, db.begin():
        row = db.get(StoredReport, report_id)
        if row is None:
            return False
        db.delete(row)
        return True


def set_share(report_id: str, share_hash: Optional[str]) -> None:
    with Session(engine()) as db, db.begin():
        db.execute(
            update(StoredReport).where(StoredReport.id == report_id)
            .values(share_hash=share_hash, shared_at=_now() if share_hash else None)
        )


def load_shared(share_hash: str) -> Optional[Dict[str, Any]]:
    with Session(engine()) as db:
        row = db.execute(select(StoredReport).where(StoredReport.share_hash == share_hash)).scalar_one_or_none()
        if row is None:
            return None
        try:
            data = json.loads(row.data)
        except (TypeError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        data["report_id"] = row.id
        return data


def transfer(from_owner: str, to_owner: str) -> int:
    """Move every report from one owner to another. Returns how many moved."""
    with Session(engine()) as db, db.begin():
        rows = db.execute(select(StoredReport).where(StoredReport.owner_hash == from_owner)).scalars().all()
        for row in rows:
            row.owner_hash = to_owner
            try:
                data = json.loads(row.data)
                if isinstance(data, dict):
                    data[OWNER_KEY] = to_owner
                    row.data = json.dumps(data, default=str, ensure_ascii=False)
            except (TypeError, ValueError):
                pass
        return len(rows)


def import_files(folder: str = "storage/reports") -> int:
    """
    One-off move of reports saved as files by older versions into the
    database. Files already imported are skipped; files are left in place.
    """
    root = Path(folder)
    if not root.is_dir():
        return 0
    moved = 0
    for path in sorted(root.glob("*.json")):
        report_id = path.stem
        try:
            if get_row(report_id) is not None:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            save(report_id, data)
            moved += 1
        except Exception as e:  # one bad file mustn't stop the rest
            logger.warning("report_store.import_failed file=%s error=%s", path.name, e)
    if moved:
        logger.info("report_store.imported %s report file(s) into the database", moved)
    return moved
