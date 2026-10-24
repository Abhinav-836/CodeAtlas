"""
JSON export for analysis reports.
"""
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

from app.core.owner import OWNER_KEY, same_owner


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
    """
    Load report from file.

    Args:
        report_id: Report ID

    Returns:
        Report data or None if not found
    """
    possible_paths = [
        Path(f"storage/reports/{report_id}.json"),
        Path(f"storage/reports/{report_id}"),
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
    Save analysis report as JSON file.

    Args:
        data: Analysis data
        report_id: Optional report ID (generated if not provided)

    Returns:
        Report ID
    """
    import uuid

    if report_id is None:
        if 'analysis_id' in data:
            report_id = data['analysis_id']
        else:
            report_id = f"report_{uuid.uuid4().hex[:8]}"

    reports_dir = Path("storage/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    data = _add_export_metadata(data, report_id)
    filename = reports_dir / f"{report_id}.json"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        return report_id
    except Exception as e:
        raise RuntimeError(f"Failed to save JSON report: {str(e)}")


def _report_stats(data: Dict[str, Any]) -> Dict[str, Any]:
    """Headline numbers, read from where the analyzer actually stores them."""
    metrics = data.get('metrics', {}) or {}
    summary = data.get('summary', {}) or {}
    security = data.get('security', {}) or {}
    return {
        'risk_level': data.get('overall_risk_level') or metrics.get('risk', 'unknown'),
        'risk_score': data.get('overall_risk_score', metrics.get('risk_score', 0)),
        'files_analyzed': summary.get('files_analyzed', summary.get('total_files', 0)),
        'total_lines': metrics.get('total_lines', 0),
        'secrets_found': security.get('secrets_found', 0),
        'vulnerabilities_found': security.get('vulnerabilities_found', 0),
    }


def get_report_list(limit: int = 50, owner: Optional[str] = None) -> Dict[str, Any]:
    """
    Get list of available reports, newest first.

    Args:
        limit: Maximum number of reports to return
        owner: If given, only reports stamped with this owner hash

    Returns:
        Dictionary with report list
    """
    reports_dir = Path("storage/reports")

    if not reports_dir.exists():
        return {"reports": [], "total": 0, "limit": limit}

    reports = []

    json_files = sorted(
        reports_dir.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, dict):
                continue

            # Only the caller's own reports. Reports with no owner (made
            # before ownership existed) are visible to nobody.
            if owner is not None and not same_owner(data.get(OWNER_KEY), owner):
                continue

            stat = json_file.stat()

            report_info = {
                'id': json_file.stem,
                'filename': json_file.name,
                'size_kb': stat.st_size / 1024,
                'size_bytes': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                'path': data.get('path', 'Unknown'),
                'analysis_id': data.get('analysis_id', json_file.stem),
                'repo_name': data.get('repo_name'),
                **_report_stats(data),
            }

            reports.append(report_info)

            if len(reports) >= limit:
                break

        except (IOError, json.JSONDecodeError, UnicodeDecodeError):
            continue

    return {"reports": reports, "total": len(reports), "limit": limit}


def delete_report(report_id: str) -> bool:
    """Delete a report file. Returns True if deleted."""
    report_file = Path("storage/reports") / f"{report_id}.json"

    if not report_file.exists():
        return False

    try:
        report_file.unlink()
        return True
    except Exception:
        return False


def get_report_metadata(report_id: str) -> Optional[Dict[str, Any]]:
    """
    Get report metadata, or None if not found.

    NOTE: does not check ownership - callers that serve this to a user
    must check it (the reports router does).
    """
    report_file = Path(f"storage/reports/{report_id}.json")

    if not report_file.exists():
        return None

    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return None

        stat = report_file.stat()

        return {
            'id': report_id,
            'filename': report_file.name,
            'size_bytes': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
            'path': data.get('path', 'Unknown'),
            'analysis_id': data.get('analysis_id', report_id),
            'status': data.get('status', 'unknown'),
            'timestamp': data.get('timestamp', 'unknown'),
            'repo_name': data.get('repo_name'),
            **_report_stats(data),
        }

    except (IOError, json.JSONDecodeError, UnicodeDecodeError):
        return None