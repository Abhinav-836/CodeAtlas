"""
Report endpoints for exporting analysis results.
"""
import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, StreamingResponse
from fastapi.encoders import jsonable_encoder

from app.services.export.json import (
    export_json, 
    get_report_list, 
    get_report_metadata, 
    delete_report, 
    save_json_report
)
from app.services.export.html import export_html
from app.services.export.markdown import export_markdown
from app.services.export.pdf import export_pdf, export_pdf_to_file

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=Dict[str, Any])
async def list_reports(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort: str = Query("created", description="Sort by: created, modified, size, name"),
    order: str = Query("desc", description="Order: asc or desc")
) -> Dict[str, Any]:
    """
    List available analysis reports with pagination and sorting.
    
    Args:
        limit: Maximum number of reports to return
        offset: Pagination offset
        sort: Field to sort by
        order: Sort order (asc/desc)
        
    Returns:
        List of reports with metadata
    """
    try:
        # Get all reports
        all_reports_result = await asyncio.to_thread(get_report_list, limit=10000)
        reports = all_reports_result.get("reports", [])
        
        # Apply sorting
        reverse = order.lower() == "desc"
        
        if sort == "created":
            reports.sort(key=lambda x: x.get("created", ""), reverse=reverse)
        elif sort == "modified":
            reports.sort(key=lambda x: x.get("modified", ""), reverse=reverse)
        elif sort == "size":
            reports.sort(key=lambda x: x.get("size_bytes", 0), reverse=reverse)
        elif sort == "name":
            reports.sort(key=lambda x: x.get("filename", "").lower(), reverse=reverse)
        
        # Apply pagination
        total = len(reports)
        paginated_reports = reports[offset:offset + limit]
        
        return {
            "reports": paginated_reports,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
                "total_pages": (total + limit - 1) // limit,
                "current_page": (offset // limit) + 1
            },
            "sorting": {
                "by": sort,
                "order": order
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list reports: {str(e)}"
        )


@router.get("/search")
async def search_reports(
    query: str = Query("", description="Search in report metadata and content"),
    risk_level: str = Query(None, description="Filter by risk level (low, medium, high, critical)"),
    min_score: float = Query(None, ge=0, le=100, description="Minimum risk score"),
    max_score: float = Query(None, ge=0, le=100, description="Maximum risk score"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
) -> Dict[str, Any]:
    """
    Search and filter reports.
    
    Args:
        query: Search text
        risk_level: Filter by risk level
        min_score: Minimum risk score
        max_score: Maximum risk score
        date_from: Filter from date
        date_to: Filter to date
        
    Returns:
        Filtered reports
    """
    try:
        all_reports_result = await asyncio.to_thread(get_report_list, limit=10000)
        reports = all_reports_result.get("reports", [])
        
        filtered_reports = []
        
        for report in reports:
            # Apply text search
            if query:
                search_fields = [
                    report.get("filename", ""),
                    report.get("path", ""),
                    report.get("analysis_id", "")
                ]
                if not any(query.lower() in field.lower() for field in search_fields):
                    # Try to load summary for deeper search
                    try:
                        summary = await get_report_summary(report.get("id"))
                        content_str = json.dumps(summary, default=str)
                        if query.lower() not in content_str.lower():
                            continue
                    except:
                        continue
            
            # Apply risk level filter
            if risk_level:
                if report.get("risk_level", "").lower() != risk_level.lower():
                    continue
            
            # Apply score filters
            if min_score is not None:
                if report.get("risk_score", 0) < min_score:
                    continue
            
            if max_score is not None:
                if report.get("risk_score", 100) > max_score:
                    continue
            
            # Apply date filters
            if date_from or date_to:
                created_date = report.get("created", "").split("T")[0] if report.get("created") else ""
                
                if date_from and created_date < date_from:
                    continue
                
                if date_to and created_date > date_to:
                    continue
            
            filtered_reports.append(report)
        
        return {
            "reports": filtered_reports,
            "total": len(filtered_reports),
            "query": query,
            "filters": {
                "risk_level": risk_level,
                "min_score": min_score,
                "max_score": max_score,
                "date_from": date_from,
                "date_to": date_to
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/{report_id}")
async def get_report(
    report_id: str, 
    format: str = Query("json", description="Output format: json, html, markdown, pdf"),
    download: bool = Query(False, description="Force download as file")
):
    """
    Get analysis report in specified format.
    
    Args:
        report_id: Report ID
        format: Output format
        download: Force file download
        
    Returns:
        Report in requested format
    """
    try:
        # Get JSON report first
        json_str = await asyncio.to_thread(export_json, report_id)
        
        try:
            report_data = json.loads(json_str)
            if "error" in report_data:
                raise HTTPException(404, detail=report_data["error"])
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Invalid JSON in report: {str(e)}"
            )
        
        # Determine filename
        repo_name = report_data.get("path", "unknown").split("/")[-1]
        timestamp = report_data.get("timestamp", datetime.now().isoformat())[:19].replace(":", "-")
        filename = f"{repo_name}_{timestamp}"
        
        # Return in requested format
        if format == "json":
            if download:
                content = json.dumps(report_data, indent=2, ensure_ascii=False)
                return StreamingResponse(
                    iter([content]),
                    media_type="application/json",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}.json"'
                    }
                )
            return JSONResponse(
                content=jsonable_encoder(report_data),
                media_type="application/json"
            )
            
        elif format == "html":
            html_content = await asyncio.to_thread(export_html, report_data)
            
            if download:
                return HTMLResponse(
                    content=html_content,
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}.html"'
                    }
                )
            return HTMLResponse(content=html_content)
            
        elif format == "markdown":
            md_content = await asyncio.to_thread(export_markdown, report_data)
            
            if download:
                return StreamingResponse(
                    iter([md_content]),
                    media_type="text/markdown",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}.md"'
                    }
                )
            
            return JSONResponse(content={
                "content": md_content,
                "filename": f"{filename}.md",
                "format": "markdown",
                "size": len(md_content)
            })
            
        elif format == "pdf":
            pdf_bytes = await asyncio.to_thread(export_pdf, report_data)
            
            if not pdf_bytes:
                raise HTTPException(
                    status_code=500,
                    detail="PDF generation failed. Make sure reportlab is installed."
                )
            
            return StreamingResponse(
                iter([pdf_bytes]),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}.pdf"'
                }
            )
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format}. Supported: json, html, markdown, pdf"
            )
            
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Report {report_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get report: {str(e)}"
        )


@router.get("/{report_id}/preview")
async def get_report_preview(report_id: str) -> Dict[str, Any]:
    """
    Get a preview of the report (first N lines/key sections).
    
    Args:
        report_id: Report ID
        
    Returns:
        Report preview
    """
    try:
        metadata = await asyncio.to_thread(get_report_metadata, report_id)
        
        if not metadata:
            raise HTTPException(404, detail=f"Report {report_id} not found")
        
        # Try to get first part of the report
        report_file = Path(f"storage/reports/{report_id}.json")
        if not report_file.exists():
            return {"metadata": metadata, "preview_available": False}
        
        # Read first 10KB for preview
        def read_preview():
            with open(report_file, 'r', encoding='utf-8') as f:
                preview_content = f.read(10240)
                try:
                    data = json.loads(preview_content + "}")
                    return data
                except json.JSONDecodeError:
                    # Return as text preview if not valid JSON
                    return {"preview_text": preview_content[:1000] + "..."}
        
        preview_data = await asyncio.to_thread(read_preview)
        
        return {
            "metadata": metadata,
            "preview": preview_data,
            "preview_available": True,
            "full_report_url": f"/reports/{report_id}?format=json"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get preview: {str(e)}"
        )


@router.get("/{report_id}/metadata")
async def get_report_metadata_endpoint(report_id: str) -> Dict[str, Any]:
    """
    Get detailed report metadata.
    
    Args:
        report_id: Report ID
        
    Returns:
        Complete report metadata
    """
    metadata = await asyncio.to_thread(get_report_metadata, report_id)
    
    if not metadata:
        raise HTTPException(
            status_code=404,
            detail=f"Report {report_id} not found"
        )
    
    # Add additional calculated metadata
    report_file = Path(f"storage/reports/{report_id}.json")
    if report_file.exists():
        file_stats = report_file.stat()
        metadata.update({
            "size_human": _human_readable_size(file_stats.st_size),
            "created": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            "permissions": oct(file_stats.st_mode)[-3:],
        })
    
    return metadata


@router.delete("/{report_id}")
async def delete_report_endpoint(report_id: str) -> Dict[str, Any]:
    """
    Delete a report.
    
    Args:
        report_id: Report ID
        
    Returns:
        Deletion result
    """
    try:
        # Get metadata before deletion for response
        metadata = await asyncio.to_thread(get_report_metadata, report_id)
        
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Report {report_id} not found"
            )
        
        deleted = await asyncio.to_thread(delete_report, report_id)
        
        if not deleted:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete report {report_id}"
            )
        
        return {
            "deleted": True,
            "report_id": report_id,
            "filename": metadata.get("filename", "unknown"),
            "size_bytes": metadata.get("size_bytes", 0),
            "message": f"Report {report_id} deleted successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete report: {str(e)}"
        )


@router.post("/{report_id}/export")
async def export_report_file(
    report_id: str, 
    format: str = Query("json", description="Export format"),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Export report to a file and return download info.
    
    Args:
        report_id: Report ID
        format: Output format
        background_tasks: Background tasks for cleanup
        
    Returns:
        Export information with download link
    """
    try:
        # Verify report exists
        metadata = await asyncio.to_thread(get_report_metadata, report_id)
        if not metadata:
            raise HTTPException(404, detail=f"Report {report_id} not found")
        
        # Get report data
        json_str = await asyncio.to_thread(export_json, report_id)
        report_data = json.loads(json_str)
        
        if "error" in report_data:
            raise HTTPException(404, detail=report_data["error"])
        
        # Create export directory
        export_dir = Path("storage/exports")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean old exports (keep last 100)
        await _cleanup_old_exports(export_dir, keep_last=100)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        repo_name = report_data.get("path", "unknown").split("/")[-1].replace(" ", "_")
        safe_repo_name = "".join(c for c in repo_name if c.isalnum() or c in "._-")
        filename = f"{safe_repo_name}_{report_id[:8]}_{timestamp}.{format}"
        filepath = export_dir / filename
        
        # Export based on format
        export_functions = {
            "json": lambda: filepath.write_text(
                json.dumps(report_data, indent=2, ensure_ascii=False, default=str),
                encoding='utf-8'
            ),
            "html": lambda: filepath.write_text(
                export_html(report_data),
                encoding='utf-8'
            ),
            "markdown": lambda: filepath.write_text(
                export_markdown(report_data),
                encoding='utf-8'
            ),
            "pdf": lambda: export_pdf_to_file(report_data, str(filepath))
        }
        
        if format not in export_functions:
            raise HTTPException(400, detail=f"Unsupported format: {format}")
        
        success = await asyncio.to_thread(export_functions[format])
        
        if format == "pdf" and not success:
            raise HTTPException(500, detail="PDF generation failed")
        
        # Get file info
        file_size = filepath.stat().st_size
        
        # Schedule cleanup after 24 hours
        if background_tasks:
            background_tasks.add_task(
                _delete_export_after_delay,
                filepath,
                delay_hours=24
            )
        
        return {
            "exported": True,
            "report_id": report_id,
            "format": format,
            "filename": filename,
            "filepath": str(filepath),
            "size_bytes": file_size,
            "size_human": _human_readable_size(file_size),
            "download_url": f"/reports/download/{filename}",
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "message": f"Report exported as {format.upper()}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_exported_file(filename: str):
    """
    Download an exported report file.
    
    Args:
        filename: Export filename
        
    Returns:
        File download with appropriate headers
    """
    filepath = Path("storage/exports") / filename
    
    if not filepath.exists():
        raise HTTPException(404, detail=f"File {filename} not found")
    
    # Security check: ensure file is in exports directory
    try:
        filepath.resolve().relative_to(Path("storage/exports").resolve())
    except ValueError:
        raise HTTPException(403, detail="Access denied")
    
    # Determine content type
    content_types = {
        '.json': 'application/json',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.md': 'text/markdown',
        '.markdown': 'text/markdown',
        '.pdf': 'application/pdf',
        '.txt': 'text/plain'
    }
    
    ext = filepath.suffix.lower()
    media_type = content_types.get(ext, 'application/octet-stream')
    
    # Add cache headers for exports
    headers = {
        "Cache-Control": "private, max-age=3600",  # 1 hour cache
        "X-Content-Type-Options": "nosniff"
    }
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=media_type,
        headers=headers
    )


@router.get("/{report_id}/summary")
async def get_report_summary(report_id: str) -> Dict[str, Any]:
    """
    Get comprehensive report summary.
    
    Args:
        report_id: Report ID
        
    Returns:
        Report summary with key metrics
    """
    try:
        metadata = await asyncio.to_thread(get_report_metadata, report_id)
        
        if not metadata:
            raise HTTPException(404, detail=f"Report {report_id} not found")
        
        # Try to load full report for summary
        report_file = Path(f"storage/reports/{report_id}.json")
        if not report_file.exists():
            return {"metadata": metadata, "content_available": False}
        
        def load_report_for_summary():
            with open(report_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Extract key metrics
                metrics = data.get("metrics", {})
                security = data.get("security", {})
                complexity = data.get("complexity", {})
                dependencies = data.get("dependencies", {})
                
                summary = {
                    "id": report_id,
                    "analysis_id": data.get("analysis_id", report_id),
                    "path": data.get("path", "Unknown"),
                    "timestamp": data.get("timestamp", metadata.get("created")),
                    "status": data.get("status", "completed"),
                    
                    # File metrics
                    "files_analyzed": data.get("files_analyzed", 0),
                    "total_lines": data.get("total_lines", 0),
                    "total_size_bytes": data.get("total_size_bytes", 0),
                    
                    # Risk assessment
                    "risk_level": metrics.get("risk", "unknown"),
                    "risk_score": metrics.get("risk_score", 0),
                    "risk_factors": metrics.get("risk_factors", []),
                    
                    # Security findings
                    "secrets_found": security.get("secrets_found", 0),
                    "vulnerabilities_found": security.get("vulnerabilities_found", 0),
                    "critical_issues": security.get("critical_issues", 0),
                    
                    # Complexity metrics
                    "avg_complexity": complexity.get("average_complexity", 0),
                    "high_complexity_files": complexity.get("high_complexity_files", 0),
                    
                    # Dependency metrics
                    "total_dependencies": dependencies.get("total", 0),
                    "vulnerable_dependencies": dependencies.get("vulnerable", 0),
                    "outdated_dependencies": dependencies.get("outdated", 0),
                    
                    # File types
                    "file_types": data.get("file_types", {}),
                    
                    # Size info
                    "size_bytes": metadata.get("size_bytes", 0),
                    "size_human": _human_readable_size(metadata.get("size_bytes", 0)),
                    "created": metadata.get("created"),
                    "modified": metadata.get("modified"),
                }
                
                return summary
        
        summary = await asyncio.to_thread(load_report_for_summary)
        summary["content_available"] = True
        
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get summary: {str(e)}"
        )


@router.post("/save")
async def save_report_manually(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Manually save a report (for debugging or external analysis).
    
    Args:
        report_data: Analysis data to save
        
    Returns:
        Save result with report URL
    """
    try:
        # Validate required fields
        required_fields = ["path", "timestamp", "files_analyzed"]
        for field in required_fields:
            if field not in report_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        report_id = await asyncio.to_thread(save_json_report, report_data)
        
        return {
            "saved": True,
            "report_id": report_id,
            "message": f"Report saved with ID: {report_id}",
            "urls": {
                "json": f"/reports/{report_id}?format=json",
                "html": f"/reports/{report_id}?format=html",
                "metadata": f"/reports/{report_id}/metadata",
                "summary": f"/reports/{report_id}/summary"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save report: {str(e)}"
        )


@router.delete("/exports/cleanup")
async def cleanup_exports(
    older_than_days: int = Query(7, ge=1, le=365, description="Delete exports older than X days")
) -> Dict[str, Any]:
    """
    Clean up old export files.
    
    Args:
        older_than_days: Delete files older than this many days
        
    Returns:
        Cleanup results
    """
    try:
        export_dir = Path("storage/exports")
        if not export_dir.exists():
            return {"cleaned": True, "deleted": 0, "message": "Export directory does not exist"}
        
        cutoff_time = datetime.now().timestamp() - (older_than_days * 24 * 3600)
        deleted_files = []
        
        for file_path in export_dir.glob("*.*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_files.append(file_path.name)
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")
        
        return {
            "cleaned": True,
            "deleted_count": len(deleted_files),
            "deleted_files": deleted_files,
            "older_than_days": older_than_days,
            "message": f"Deleted {len(deleted_files)} export files older than {older_than_days} days"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )


# Helper functions
def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


async def _cleanup_old_exports(export_dir: Path, keep_last: int = 100):
    """Clean up old export files, keeping only the most recent ones."""
    try:
        if not export_dir.exists():
            return
        
        # Get all export files sorted by modification time
        export_files = sorted(
            export_dir.glob("*.*"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        # Delete files beyond keep_last
        for file_path in export_files[keep_last:]:
            try:
                file_path.unlink()
            except Exception as e:
                print(f"Failed to delete old export {file_path}: {e}")
                
    except Exception as e:
        print(f"Export cleanup failed: {e}")


async def _delete_export_after_delay(filepath: Path, delay_hours: int = 24):
    """Delete export file after specified delay."""
    await asyncio.sleep(delay_hours * 3600)
    
    try:
        if filepath.exists():
            filepath.unlink()
            print(f"Cleaned up expired export: {filepath.name}")
    except Exception as e:
        print(f"Failed to delete expired export {filepath}: {e}")


# Import timedelta for expiration
from datetime import timedelta