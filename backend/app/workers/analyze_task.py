"""
Analysis task implementation for code repositories.
"""
import os
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.analysis.architecture import infer_architecture
from app.services.analysis.complexity_analyzer import analyze_files
from app.services.analysis.metrics import code_metrics
from app.services.security.secrets_scanner import (
    scan_secrets,
    scan_secrets_git_history,
    summarize_findings as summarize_secrets,
)
from app.services.security.vuln_patterns import (
    scan_vulnerabilities,
    summarize_vulnerabilities,
)


def analyze_repo(repo_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    start_time = time.time()
    analysis_id = f"analysis_{int(start_time)}_{os.urandom(4).hex()}"

    try:
        print(f"🔍 Starting analysis {analysis_id} of: {repo_path}")

        path_obj = Path(repo_path).resolve()
        if not path_obj.exists() or not path_obj.is_dir():
            return {
                "error": f"Invalid path: {repo_path}",
                "status": "failed",
                "analysis_id": analysis_id,
                "timestamp": datetime.now().isoformat(),
            }

        result: Dict[str, Any] = {
            "analysis_id": analysis_id,
            "path": str(path_obj),
            "repo_name": path_obj.name,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "options": options or {},
        }

        print(f"📁 Scanning files in: {repo_path}")
        all_files = _scan_all_files(repo_path)
        if not all_files:
            return {
                "error": "No files found to analyze",
                "status": "completed",
                "analysis_id": analysis_id,
                "path": repo_path,
                "timestamp": datetime.now().isoformat(),
            }
        print(f"📊 Found {len(all_files)} files to analyze")

        result["summary"] = {
            "total_files": len(all_files),
            "files_analyzed": len(all_files),
            "scanned_at": datetime.now().isoformat(),
            "total_size_bytes": sum(
                Path(f).stat().st_size for f in all_files if Path(f).exists()
            ),
        }

        print("📈 Calculating metrics...")
        result["metrics"] = code_metrics(all_files)

        print("🏗️  Analyzing architecture...")
        result["architecture"] = infer_architecture(all_files)

        print("🔒 Scanning for secrets...")
        secrets_found = scan_secrets(all_files)
        print("🕓 Scanning git history for secrets...")
        history_secrets_found = scan_secrets_git_history(repo_path)
        all_secrets = secrets_found + history_secrets_found
        secrets_summary = summarize_secrets(all_secrets)

        print("⚠️  Scanning for vulnerabilities...")
        vulns = scan_vulnerabilities(all_files)
        vulns_summary = summarize_vulnerabilities(vulns)

        # secrets_summary and vulns_summary both use the keys
        # total_findings / by_type / critical_findings / high_findings for
        # their own (different) data. Flattening both into one dict via
        # .update() silently drops one side - a repo with critical
        # hardcoded secrets but zero flagged vulnerabilities would end up
        # reporting zero critical findings overall. Keep each summary
        # under its own key instead of merging them into the same names.
        result["security"] = {
            "secrets_found": len(all_secrets),
            "secrets_found_working_tree": len(secrets_found),
            "secrets_found_git_history": len(history_secrets_found),
            "secrets": all_secrets[:20],
            "vulnerabilities_found": len(vulns),
            "vulnerabilities": vulns[:20],
            # Vulnerability severity counts - used directly by the results
            # UI's security tab and pie chart.
            "by_severity": vulns_summary.get("by_severity", {}),
            "risk_level": secrets_summary.get("risk_level", "none"),
            "secrets_summary": secrets_summary,
            "vulnerabilities_summary": vulns_summary,
        }

        secrets_critical = secrets_summary.get("critical_findings") or []
        vulns_critical = vulns_summary.get("critical_findings") or []
        critical_count = (
            (len(secrets_critical) if isinstance(secrets_critical, list) else 0)
            + (len(vulns_critical) if isinstance(vulns_critical, list) else 0)
        )
        result["security"]["overall_risk"] = (
            "critical" if critical_count > 0
            else "high" if result["security"].get("vulnerabilities_found", 0) > 0
            else "medium" if result["security"].get("secrets_found", 0) > 5
            else "low" if result["security"].get("secrets_found", 0) > 0
            else "none"
        )

        print("🌐 Analyzing language-specific features...")
        result["languages"] = _analyze_languages(all_files)

        print("📊 Computing complexity across all languages...")
        result["complexity"] = analyze_files(all_files)
        # Aliases for backward compatibility with old report consumers.
        py_bucket = result["complexity"]["per_language"].get("Python")
        js_bucket = (
            result["complexity"]["per_language"].get("JavaScript")
            or result["complexity"]["per_language"].get("TypeScript")
        )
        if py_bucket:
            result["python_analysis"] = py_bucket
        if js_bucket:
            result["javascript_analysis"] = js_bucket

        result["overall_risk_score"] = _calculate_overall_risk_score(result)
        result["overall_risk_level"] = _get_risk_level(result["overall_risk_score"])

        end_time = time.time()
        result["performance"] = {
            "analysis_duration_seconds": round(end_time - start_time, 2),
            "files_per_second": round(len(all_files) / (end_time - start_time), 2)
            if (end_time - start_time) > 0 else 0,
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
        }

        result["recommendations"] = _generate_recommendations(result)

        print(
            f"✅ Analysis {analysis_id} completed in "
            f"{result['performance']['analysis_duration_seconds']}s"
        )
        return result

    except Exception as e:
        print(f"❌ Analysis {analysis_id} failed: {str(e)}")
        print(traceback.format_exc())
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "path": repo_path,
            "status": "failed",
            "analysis_id": analysis_id,
            "timestamp": datetime.now().isoformat(),
        }


def _scan_all_files(repo_path: str) -> List[str]:
    all_files: List[str] = []
    print(f"🔍 Scanning directory: {repo_path}")
    if not os.path.exists(repo_path):
        return all_files
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and d not in {"__pycache__", "node_modules", ".git",
                                 "venv", ".venv", "env", "dist", "build",
                                 ".next", ".nuxt", "target"}]
        for file in files:
            if file.startswith("."):
                continue
            all_files.append(os.path.join(root, file))
    print(f"✅ Total files found: {len(all_files)}")
    return all_files


def _analyze_languages(all_files: List[str]) -> Dict[str, Any]:
    from app.services.analysis.complexity_analyzer import LANGUAGE_BY_EXT
    lang_map = {ext: lang for ext, lang in LANGUAGE_BY_EXT.items()}
    # Non-source extensions we still want to count for the language pie
    lang_map.update({
        ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".sass": "SASS",
        ".json": "JSON", ".yml": "YAML", ".yaml": "YAML", ".xml": "XML",
        ".md": "Markdown", ".txt": "Text", ".sql": "SQL",
        ".dockerfile": "Docker",
    })

    stats: Dict[str, int] = {}
    total = len(all_files)
    for fp in all_files:
        ext = Path(fp).suffix.lower()
        lang = lang_map.get(ext)
        if lang:
            stats[lang] = stats.get(lang, 0) + 1

    with_pct = {}
    for lang, count in stats.items():
        with_pct[lang] = {
            "count": count,
            "percentage": round((count / total) * 100, 2) if total else 0,
        }
    ordered = dict(sorted(with_pct.items(), key=lambda x: x[1]["count"], reverse=True))
    return {
        "detected_languages": ordered,
        "primary_language": next(iter(ordered), "Unknown"),
        "language_count": len(ordered),
    }


def _calculate_overall_risk_score(result: Dict[str, Any]) -> int:
    """
    Weighted 0-100 risk score. Every category of finding contributes so
    the score agrees with the recommendations panel.
    """
    score = 0
    security = result.get("security", {}) or {}

    secrets = security.get("secrets_found", 0) or 0
    score += min(secrets * 5, 30)

    by_sev = security.get("by_severity", {}) or {}
    score += min(by_sev.get("critical", 0) * 15, 30)
    score += min(by_sev.get("high", 0) * 8, 25)
    score += min(by_sev.get("medium", 0) * 3, 15)

    cx = result.get("complexity", {}) or {}
    avg = cx.get("avg_complexity_score", 0) or 0
    if avg > 50:
        score += 15
    elif avg > 20:
        score += 8
    elif avg > 10:
        score += 3

    files = (result.get("summary", {}) or {}).get("total_files", 0) or 0
    if files > 1000:
        score += 10
    elif files > 500:
        score += 5

    return min(score, 100)


def _get_risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 20:
        return "low"
    return "none"


def _generate_recommendations(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    recs: List[Dict[str, Any]] = []
    security = result.get("security", {}) or {}
    cx = result.get("complexity", {}) or {}

    if security.get("secrets_found", 0) > 0:
        recs.append({
            "category": "security", "priority": "high",
            "title": "Remove hardcoded secrets",
            "description": f"Found {security['secrets_found']} potential secrets in the codebase.",
            "action": "Review and remove or rotate exposed API keys, passwords, and tokens.",
        })

    if security.get("vulnerabilities_found", 0) > 0:
        recs.append({
            "category": "security", "priority": "high",
            "title": "Fix security vulnerabilities",
            "description": f"Found {security['vulnerabilities_found']} potential vulnerabilities.",
            "action": "Review and fix the identified security issues.",
        })

    avg = cx.get("avg_complexity_score", 0) or 0
    if avg > 20:
        recs.append({
            "category": "maintainability", "priority": "medium",
            "title": "Reduce code complexity",
            "description": f"High average complexity score: {avg}",
            "action": "Refactor complex functions; target cyclomatic complexity < 10.",
        })

    files = (result.get("summary", {}) or {}).get("total_files", 0) or 0
    if files > 1000:
        recs.append({
            "category": "architecture", "priority": "low",
            "title": "Consider modularization",
            "description": f"Large codebase with {files} files.",
            "action": "Split into smaller, focused modules or services.",
        })

    return recs