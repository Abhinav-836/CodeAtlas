"""
JSON export for analysis reports.
"""
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime



def export_json(report_id: str, report_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Export analysis report as JSON.

    Args:
        report_id: Report ID for reference
        report_data: Analysis report data (if None, tries to load from file)

    Returns:
        JSON string
    """
    try:
        if report_data:
            data = report_data
        else:
            data = _load_report_from_file(report_id)
            if not data:
                return json.dumps({
                    "error": f"Report {report_id} not found",
                    "status": "not_found"
                }, indent=2)

        data = _add_export_metadata(data, report_id)
        return json.dumps(data, indent=2, default=str)

    except Exception as e:
        error_data = {
            "error": f"Failed to export JSON: {str(e)}",
            "report_id": report_id,
            "status": "error"
        }
        return json.dumps(error_data, indent=2)


def _load_report_from_file(report_id: str) -> Optional[Dict[str, Any]]:
    """Load a report: from the database, or from an analysis file on disk."""
    from app.services import report_store

    data = report_store.load(report_id)
    if data is not None:
        return data

    possible_paths = [
        Path(f"storage/uploads/{report_id}/analysis.json"),
        Path(f"storage/repos/{report_id}/analysis.json"),
    ]
    for path in possible_paths:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict) and ('path' in data or 'analysis_id' in data):
                    return data
            except (json.JSONDecodeError, IOError, UnicodeDecodeError):
                continue
    return None


def _add_export_metadata(data: Dict[str, Any], report_id: str) -> Dict[str, Any]:
    """
    Add export metadata to report.

    Args:
        data: Report data
        report_id: Report ID

    Returns:
        Enhanced report data
    """
    if not isinstance(data, dict):
        return data

    enhanced = data.copy()
    enhanced['_export'] = {
        'format': 'json',
        'exported_at': datetime.now().isoformat(),
        'report_id': report_id,
        'version': '1.0'
    }
    return _make_json_serializable(enhanced)


def _make_json_serializable(obj: Any) -> Any:
    """Recursively make object JSON serializable."""
    if isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_serializable(v) for v in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif hasattr(obj, 'isoformat'):  # datetime objects
        return obj.isoformat()
    elif isinstance(obj, Path):
        return str(obj)
    else:
        try:
            return str(obj)
        except Exception:
            return repr(obj)


def save_json_report(data: Dict[str, Any], report_id: Optional[str] = None) -> str:
    """
    Save an analysis report (to the database, so it survives redeploys).

    Returns the report ID: the given one, else the analysis ID, else a new one.
    """
    import uuid
    from app.services import report_store

    if report_id is None:
        report_id = data.get('analysis_id') or f"report_{uuid.uuid4().hex[:8]}"

    data = _add_export_metadata(data, report_id)
    try:
        report_store.save(report_id, _make_json_serializable(data))
        return report_id
    except Exception as e:
        raise RuntimeError(f"Failed to save report: {str(e)}")


def get_report_list(limit: int = 50, owner: Optional[str] = None) -> Dict[str, Any]:
    """
    The owner's reports, newest first. Without an owner there is nothing to
    list: reports with no owner (made before ownership existed) are nobody's.
    """
    from app.services import report_store

    if owner is None:
        return {"reports": [], "total": 0, "limit": limit}
    reports = report_store.list_for_owner(owner, limit)
    return {"reports": reports, "total": len(reports), "limit": limit}


def delete_report(report_id: str) -> bool:
    """Delete a report. Returns True if it existed."""
    from app.services import report_store

    return report_store.delete(report_id)


def get_report_metadata(report_id: str) -> Optional[Dict[str, Any]]:
    """
    Report metadata, or None if not found.

    NOTE: does not check ownership - callers that serve this to a user
    must check it (the reports router does).
    """
    from app.services import report_store

    row = report_store.get_row(report_id)
    return report_store.row_summary(row) if row is not None else None
