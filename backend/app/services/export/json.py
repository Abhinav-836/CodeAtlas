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
        # If report_data is provided, use it
        if report_data:
            data = report_data
        else:
            # Try to load from file
            data = _load_report_from_file(report_id)
            if not data:
                return json.dumps({
                    "error": f"Report {report_id} not found",
                    "status": "not_found"
                }, indent=2)

        # Add export metadata
        data = _add_export_metadata(data, report_id)

        # Convert to JSON
        json_str = json.dumps(data, indent=2, default=str)

        return json_str

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
    # Try multiple possible locations
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
                # Validate it's a report
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

    # Create enhanced copy
    enhanced = data.copy()

    # Add export info
    enhanced['_export'] = {
        'format': 'json',
        'exported_at': datetime.now().isoformat(),
        'report_id': report_id,
        'version': '1.0'
    }

    # Ensure all data is JSON serializable
    enhanced = _make_json_serializable(enhanced)

    return enhanced


def _make_json_serializable(obj: Any) -> Any:
    """
    Recursively make object JSON serializable.

    Args:
        obj: Any object

    Returns:
        JSON serializable version
    """
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
        # Try to convert to string, fall back to repr
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
        # Generate report ID from analysis data
        if 'analysis_id' in data:
            report_id = data['analysis_id']
        else:
            report_id = f"report_{uuid.uuid4().hex[:8]}"

    # Ensure storage directory exists
    reports_dir = Path("storage/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Add metadata
    data = _add_export_metadata(data, report_id)

    # Save to file
    filename = reports_dir / f"{report_id}.json"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        return report_id
    except Exception as e:
        raise RuntimeError(f"Failed to save JSON report: {str(e)}")


def get_report_list(limit: int = 50) -> Dict[str, Any]:
    """
    Get list of available reports.

    Reads each report file in full and pulls out the summary fields
    needed for the list view. Report files are typically small (tens of
    KB), so this is cheap - the previous "read first 5 lines and glue on
    a closing brace" approach was faster in theory but never actually
    produced valid JSON, so it silently skipped every report.

    Args:
        limit: Maximum number of reports to return

    Returns:
        Dictionary with report list
    """
    reports_dir = Path("storage/reports")

    if not reports_dir.exists():
        return {
            "reports": [],
            "total": 0,
            "limit": limit
        }

    reports = []

    # Newest first, so a `limit` cutoff shows the most recent reports
    # rather than whatever glob() happens to yield first.
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

            metrics = data.get('metrics', {}) or {}
            stat = json_file.stat()

            report_info = {
                'id': json_file.stem,
                'filename': json_file.name,
                'size_kb': stat.st_size / 1024,
                'size_bytes': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'path': data.get('path', 'Unknown'),
                'analysis_id': data.get('analysis_id', json_file.stem),
                'risk_level': metrics.get('risk', 'unknown'),
                'risk_score': metrics.get('risk_score', 0),
            }

            reports.append(report_info)

            if len(reports) >= limit:
                break

        except (IOError, json.JSONDecodeError, UnicodeDecodeError):
            continue

    return {
        "reports": reports,
        "total": len(reports),
        "limit": limit
    }


def delete_report(report_id: str) -> bool:
    """
    Delete a report.

    Args:
        report_id: Report ID

    Returns:
        True if deleted, False otherwise
    """
    reports_dir = Path("storage/reports")
    report_file = reports_dir / f"{report_id}.json"

    if not report_file.exists():
        return False

    try:
        report_file.unlink()
        return True
    except Exception:
        return False


def get_report_metadata(report_id: str) -> Optional[Dict[str, Any]]:
    """
    Get report metadata.

    Loads the full file rather than reading a fixed byte prefix and
    gluing on a closing brace - that reconstruction never produced valid
    JSON for a real (nested) report, so every call used to fail and
    return None, making every endpoint that depends on this 404.

    Args:
        report_id: Report ID

    Returns:
        Report metadata or None if not found
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

        metadata = {
            'id': report_id,
            'filename': report_file.name,
            'size_bytes': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'path': data.get('path', 'Unknown'),
            'analysis_id': data.get('analysis_id', report_id),
            'status': data.get('status', 'unknown'),
            'timestamp': data.get('timestamp', 'unknown'),
            'files_analyzed': data.get('files_analyzed', 0),
        }

        return metadata

    except (IOError, json.JSONDecodeError, UnicodeDecodeError):
        return None