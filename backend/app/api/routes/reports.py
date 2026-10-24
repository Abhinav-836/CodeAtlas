"""
Report endpoints.

Every endpoint is scoped to the caller's owner token (app/core/owner.py):
you can only list, view, download and delete reports you created.
A report that doesn't exist and a report that belongs to someone else
both return the same 404, so report IDs can't be probed.
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app.core.owner import get_owner, owns_record, strip_owner
from app.services.export.html import export_html
from app.services.export.json import delete_report, get_report_list
from app.services.export.markdown import export_markdown
from app.services.export.pdf import export_pdf

router = APIRouter(prefix="/reports", tags=["reports"])

REPORTS_DIR = Path("storage/reports")
# Report IDs are UUIDs (or legacy "report_xxxxxxxx"). Anything else is
# rejected before it gets anywhere near the filesystem.
_REPORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


# ── Helpers ──────────────────────────────────────────────────────────
def _not_found(report_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Report {report_id} not found")


def _report_file(report_id: str) -> Path:
    if not _REPORT_ID_RE.match(report_id or ""):
        raise _not_found(report_id)
    return REPORTS_DIR / f"{report_id}.json"


def _load_owned_report_sync(report_id: str, owner: str) -> Dict[str, Any]:
    path = _report_file(report_id)
    if not path.is_file():
        raise _not_found(report_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        raise _not_found(report_id)
    if not owns_record(data, owner):
        raise _not_found(report_id)
    return data


async def _load_owned_report(report_id: str, owner: str) -> Dict[str, Any]:
    return await asyncio.to_thread(_load_owned_report_sync, report_id, owner)


def _file_meta(report_id: str) -> Dict[str, Any]:
    stat = _report_file(report_id).stat()
    return {
        "size_bytes": stat.st_size,
        "size_human": _human_readable_size(stat.st_size),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


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


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    format: str = Query("json", description="Output format: json, html, markdown, pdf"),
    download: bool = Query(False, description="Force download as file"),
    owner: str = Depends(get_owner),
):
    report = strip_owner(await _load_owned_report(report_id, owner))
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