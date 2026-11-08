"""
Report endpoints.

Every endpoint is scoped to the caller's owner token (app/core/owner.py):
you can only list, view, download and delete reports you created.
A report that doesn't exist and a report that belongs to someone else
both return the same 404, so report IDs can't be probed.

Reports are stored in the database (app/services/report_store.py), so they
survive redeploys. An owner can also:
- make a read-only share link for one report (anyone with the link can view
  and download it, nothing else), and revoke it;
- move all their reports to another browser's owner key ("use on another device").
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Any, Dict, Optional

import secrets

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app.core.owner import _TOKEN_RE, get_owner, hash_token, owns_record, same_owner, strip_owner
from app.services import report_store
from app.services.export.html import export_html
from app.services.export.json import delete_report, get_report_list
from app.services.export.markdown import export_markdown
from app.services.export.pdf import export_pdf

router = APIRouter(prefix="/reports", tags=["reports"])
# Read-only access through a share link; mounted under /api as well.
shared_router = APIRouter(prefix="/shared", tags=["shared"])
# Report IDs are UUIDs (or legacy "report_xxxxxxxx"). Anything else is
# rejected before it gets anywhere near the filesystem.
_REPORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


# ── Helpers ──────────────────────────────────────────────────────────
def _not_found(report_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Report {report_id} not found")


def _check_id(report_id: str) -> None:
    if not _REPORT_ID_RE.match(report_id or ""):
        raise _not_found(report_id)


def _load_owned_report_sync(report_id: str, owner: str) -> Dict[str, Any]:
    _check_id(report_id)
    data = report_store.load(report_id)
    if data is None or not owns_record(data, owner):
        raise _not_found(report_id)
    return data


async def _load_owned_report(report_id: str, owner: str) -> Dict[str, Any]:
    return await asyncio.to_thread(_load_owned_report_sync, report_id, owner)


def _file_meta(report_id: str) -> Dict[str, Any]:
    row = report_store.get_row(report_id)
    if row is None:
        return {}
    meta = report_store.row_summary(row)
    return {k: meta[k] for k in ("size_bytes", "size_human", "created", "modified", "shared")}


def _safe_filename(report: Dict[str, Any]) -> str:
    name = str(report.get("repo_name") or report.get("path") or "report")
    name = name.replace("\\", "/").split("/")[-1]
    name = re.sub(r"_[0-9a-f]{8}$", "", name)  # strip upload/clone suffix
    name = "".join(c for c in name if c.isalnum() or c in "._-") or "report"
    stamp = str(report.get("timestamp") or datetime.now().isoformat())[:19]
    return f"{name}_{stamp.replace(':', '-')}"


def _human_readable_size(size_bytes: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def _summary_from(report_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    metrics = data.get("metrics", {}) or {}
    summary = data.get("summary", {}) or {}
    security = data.get("security", {}) or {}
    complexity = data.get("complexity", {}) or {}
    languages = data.get("languages", {}) or {}
    return {
        "id": report_id,
        "filename": f"{report_id}.json",
        "analysis_id": data.get("analysis_id", report_id),
        "path": data.get("path", "Unknown"),
        "repo_name": data.get("repo_name"),
        "timestamp": data.get("timestamp"),
        "status": data.get("status", "completed"),
        "risk_level": data.get("overall_risk_level") or metrics.get("risk", "unknown"),
        "risk_score": data.get("overall_risk_score", metrics.get("risk_score", 0)),
        "files_analyzed": summary.get("files_analyzed", summary.get("total_files", 0)),
        "total_lines": metrics.get("total_lines", 0),
        "total_size_bytes": summary.get("total_size_bytes", 0),
        "secrets_found": security.get("secrets_found", 0),
        "vulnerabilities_found": security.get("vulnerabilities_found", 0),
        "critical_issues": (security.get("by_severity") or {}).get("critical", 0),
        "avg_complexity": complexity.get("avg_complexity_score", 0),
        "primary_language": languages.get("primary_language"),
        "language_count": languages.get("language_count", 0),
        "recommendations": data.get("recommendations", []),
        **_file_meta(report_id),
    }


# ── Endpoints ────────────────────────────────────────────────────────
@router.get("", response_model=Dict[str, Any])
async def list_reports(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort: str = Query("created", description="Sort by: created, modified, size, name"),
    order: str = Query("desc", description="Order: asc or desc"),
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    try:
        result = await asyncio.to_thread(get_report_list, 10000, owner)
        reports = result.get("reports", [])

        reverse = order.lower() == "desc"
        sort_keys = {
            "created": lambda x: x.get("created", ""),
            "modified": lambda x: x.get("modified", ""),
            "size": lambda x: x.get("size_bytes", 0),
            "name": lambda x: (x.get("repo_name") or x.get("filename", "")).lower(),
        }
        if sort in sort_keys:
            reports.sort(key=sort_keys[sort], reverse=reverse)

        total = len(reports)
        return {
            "reports": reports[offset : offset + limit],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
                "total_pages": (total + limit - 1) // limit,
                "current_page": (offset // limit) + 1,
            },
            "sorting": {"by": sort, "order": order},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {str(e)}")


@router.get("/search")
async def search_reports(
    query: str = Query("", description="Search in your reports"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    try:
        result = await asyncio.to_thread(get_report_list, 10000, owner)
        q = query.strip().lower()

        filtered = []
        for report in result.get("reports", []):
            if q:
                fields = [
                    report.get("repo_name") or "",
                    report.get("path") or "",
                    report.get("analysis_id") or "",
                    report.get("risk_level") or "",
                ]
                if not any(q in str(f).lower() for f in fields):
                    continue
            if risk_level and str(report.get("risk_level", "")).lower() != risk_level.lower():
                continue
            if min_score is not None and report.get("risk_score", 0) < min_score:
                continue
            if max_score is not None and report.get("risk_score", 100) > max_score:
                continue
            created_date = str(report.get("created", "")).split("T")[0]
            if date_from and created_date < date_from:
                continue
            if date_to and created_date > date_to:
                continue
            filtered.append(report)

        return {
            "reports": filtered,
            "total": len(filtered),
            "query": query,
            "filters": {
                "risk_level": risk_level,
                "min_score": min_score,
                "max_score": max_score,
                "date_from": date_from,
                "date_to": date_to,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


async def _render(report: Dict[str, Any], format: str, download: bool):
    """A report (owner hash already removed) in the requested format."""
    filename = _safe_filename(report)

    def attachment(ext: str) -> Dict[str, str]:
        return {"Content-Disposition": f'attachment; filename="{filename}.{ext}"'}

    try:
        if format == "json":
            if download:
                body = json.dumps(report, indent=2, ensure_ascii=False, default=str)
                return Response(body, media_type="application/json", headers=attachment("json"))
            return JSONResponse(content=jsonable_encoder(report))

        if format == "html":
            body = await asyncio.to_thread(export_html, report)
            # HTML is always a download: rendering a report built from
            # untrusted repo content on the API's own origin is asking for
            # trouble even with escaping.
            return HTMLResponse(content=body, headers=attachment("html"))

        if format == "markdown":
            body = await asyncio.to_thread(export_markdown, report)
            if download:
                return Response(body, media_type="text/markdown", headers=attachment("md"))
            return JSONResponse(
                content={"content": body, "filename": f"{filename}.md", "format": "markdown"}
            )

        if format == "pdf":
            pdf_bytes = await asyncio.to_thread(export_pdf, report)
            if not pdf_bytes:
                raise HTTPException(status_code=500, detail="PDF generation failed.")
            return Response(pdf_bytes, media_type="application/pdf", headers=attachment("pdf"))

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}. Supported: json, html, markdown, pdf",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export report: {str(e)}")


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    format: str = Query("json", description="Output format: json, html, markdown, pdf"),
    download: bool = Query(False, description="Force download as file"),
    owner: str = Depends(get_owner),
):
    report = strip_owner(await _load_owned_report(report_id, owner))
    report.setdefault("report_id", report_id)
    return await _render(report, format, download)


@router.get("/{report_id}/summary")
async def get_report_summary(
    report_id: str,
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    data = await _load_owned_report(report_id, owner)
    try:
        return {**_summary_from(report_id, data), "content_available": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")


@router.get("/{report_id}/metadata")
async def get_report_metadata_endpoint(
    report_id: str,
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    data = await _load_owned_report(report_id, owner)
    return _summary_from(report_id, data)


@router.delete("/{report_id}")
async def delete_report_endpoint(
    report_id: str,
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    data = await _load_owned_report(report_id, owner)  # 404 unless yours
    deleted = await asyncio.to_thread(delete_report, report_id)
    if not deleted:
        raise HTTPException(status_code=500, detail=f"Failed to delete report {report_id}")
    return {
        "deleted": True,
        "report_id": report_id,
        "repo_name": data.get("repo_name"),
        "message": f"Report {report_id} deleted successfully",
        "timestamp": datetime.now().isoformat(),
    }


# ── Share links ──────────────────────────────────────────────────────
# The link carries a random token; only its SHA-256 is stored, like the
# owner token. One link per report: making a new one replaces the old one.

@router.post("/{report_id}/share")
async def share_report(report_id: str, owner: str = Depends(get_owner)) -> Dict[str, Any]:
    await _load_owned_report(report_id, owner)  # 404 unless yours
    token = secrets.token_urlsafe(24)
    await asyncio.to_thread(report_store.set_share, report_id, hash_token(token))
    return {"report_id": report_id, "share_token": token}


@router.delete("/{report_id}/share")
async def unshare_report(report_id: str, owner: str = Depends(get_owner)) -> Dict[str, Any]:
    await _load_owned_report(report_id, owner)
    await asyncio.to_thread(report_store.set_share, report_id, None)
    return {"report_id": report_id, "shared": False}


_SHARE_RE = re.compile(r"^[A-Za-z0-9_-]{20,64}$")
_SHARE_GONE = "This share link doesn't work. It may have been turned off — ask for a new one."


@shared_router.get("/{share_token}")
async def get_shared_report(
    share_token: str,
    format: str = Query("json", description="Output format: json, html, markdown, pdf"),
    download: bool = Query(False),
):
    """No owner token needed: the link itself is the permission, read-only."""
    if not _SHARE_RE.match(share_token or ""):
        raise HTTPException(status_code=404, detail=_SHARE_GONE)
    data = await asyncio.to_thread(report_store.load_shared, hash_token(share_token))
    if data is None:
        raise HTTPException(status_code=404, detail=_SHARE_GONE)
    report = strip_owner(data)
    report["shared_view"] = True
    return await _render(report, format, download)


# ── Moving reports to another device ─────────────────────────────────

@router.post("/transfer")
async def transfer_reports(
    to_key: str = Body(..., embed=True, description="The other browser's owner key"),
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    """
    Move all of this browser's reports to the owner key from another browser,
    so both see the same list once this browser switches to that key.
    """
    if not _TOKEN_RE.match(to_key or ""):
        raise HTTPException(status_code=400, detail="That key isn't valid. Copy it again from the other device.")
    target = hash_token(to_key)
    if same_owner(target, owner):
        return {"moved": 0}
    moved = await asyncio.to_thread(report_store.transfer, owner, target)
    return {"moved": moved}
