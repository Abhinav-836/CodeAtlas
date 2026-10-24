"""
Analysis endpoints.
"""
import copy
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.core.owner import OWNER_KEY, get_owner, owns_folder, same_owner, strip_owner
from app.services.export.json import save_json_report
from app.workers.analyze_task import analyze_repo
from app.workers.task_queue import task_queue

router = APIRouter(prefix="/analyze")

TASK_GONE_DETAIL = (
    "This analysis is no longer available (the server may have restarted). "
    "Please run it again."
)


# ── Path safety ───────────────────────────────────────────────────
# Only directories that THIS server created (ZIP extractions and GitHub
# clones) may be analyzed. Without this, POST /api/analyze?path=/ lets
# anyone scan the server's own filesystem - including /app/.env - and
# read the "secrets" findings back out of the public report.
def _allowed_roots() -> List[Path]:
    return [
        Path(settings.UPLOAD_DIR).resolve(),
        Path("storage/repos").resolve(),
    ]


def _resolve_safe_repo_path(path: str, owner: str) -> Path:
    if not path or not path.strip():
        raise HTTPException(status_code=400, detail="Path is required")

    repo_path = Path(path.strip()).resolve()

    for root in _allowed_roots():
        try:
            rel = repo_path.relative_to(root)
        except ValueError:
            continue
        if rel.parts:  # must be inside the root, not the root itself
            break
    else:
        raise HTTPException(
            status_code=403,
            detail="Only repositories uploaded or cloned through CodeAtlas can be analyzed.",
        )

    # Same 404 for "missing" and "someone else's", so other people's
    # upload names can't be probed.
    if not repo_path.is_dir() or not owns_folder(str(repo_path), owner):
        raise HTTPException(
            status_code=404,
            detail="Repository not found on the server. It may have been cleaned up - please upload it again.",
        )
    return repo_path


def _task_owner(status: Dict[str, Any]) -> Optional[str]:
    """Owner hash of a task: the 4th positional arg of _run_analysis_with_options."""
    args = status.get("args") or ()
    if isinstance(args, (list, tuple)) and len(args) >= 4:
        return args[3]
    result = status.get("result")
    if isinstance(result, dict):
        return result.get(OWNER_KEY)
    return None


def _get_owned_task(task_id: str, owner: str) -> Dict[str, Any]:
    status = task_queue.get_status(task_id)
    # Unknown task and someone else's task look identical to the caller.
    if not status or not same_owner(_task_owner(status), owner):
        raise HTTPException(status_code=404, detail=TASK_GONE_DETAIL)
    return status


def _relativize_paths(result: Dict[str, Any], repo_root: str) -> Dict[str, Any]:
    """
    Replace the server's absolute repo path (e.g. /opt/render/project/src/
    backend/storage/repos/x_1a2b3c4d/...) with paths relative to the repo,
    everywhere in the result. Users see "src/app.py" instead of the
    server's directory layout.
    """
    prefix = str(Path(repo_root)) + os.sep
    escaped = json.dumps(prefix)[1:-1]  # same escaping as inside the JSON
    text = json.dumps(result, default=str).replace(escaped, "")
    return json.loads(text)


@router.post("", response_model=Dict[str, Any])
async def analyze_repository(
    path: str,
    options: Optional[Dict[str, Any]] = None,
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    repo_path = _resolve_safe_repo_path(path, owner)

    try:
        analysis_id = str(uuid.uuid4())

        if options is None:
            options = {
                "include_security": True,
                "include_complexity": True,
                "generate_docs": True,
                "depth": "standard",
            }

        print(f"🔍 Starting analysis {analysis_id} for: {repo_path}")

        task_id = await task_queue.enqueue(
            _run_analysis_with_options,
            str(repo_path),
            options,
            analysis_id,
            owner,
        )

        analysis_info = {
            "analysis_id": analysis_id,
            "task_id": task_id,
            "path": str(repo_path),
            "options": options,
            "owner": owner,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "check_status_url": f"/api/analyze/status/{task_id}",
            "get_results_url": f"/api/analyze/results/{task_id}",
        }
        _store_analysis_info(analysis_id, analysis_info)

        return {
            "success": True,
            "analysis_id": analysis_id,
            "task_id": task_id,
            "status": "queued",
            "message": f"Analysis started for {repo_path.name}",
            "check_status_url": f"/api/analyze/status/{task_id}",
            "get_results_url": f"/api/analyze/results/{task_id}",
            "estimated_time": _estimate_analysis_time(repo_path, options),
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error starting analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")


def _run_analysis_with_options(
    path: str, options: Dict[str, Any], analysis_id: str, owner: str
) -> Dict[str, Any]:
    """
    Runs inside the task queue's thread pool.

    On failure this must RAISE, not return an error dict: the task queue
    marks a task "completed" whenever the function returns, so returning
    {"status": "failed"} made every failed analysis look successful.
    """
    print(f"🏃 Running analysis {analysis_id} for path: {path}")
    result = analyze_repo(path)

    if not isinstance(result, dict):
        raise RuntimeError("Analysis returned an unexpected result")
    if result.get("status") == "failed" or result.get("error"):
        raise RuntimeError(result.get("error") or "Analysis failed")

    result = _relativize_paths(result, path)
    result["path"] = Path(path).name
    result["analysis_id"] = analysis_id
    result["options_used"] = options
    result["status"] = "completed"
    result["completed_at"] = datetime.now().isoformat()
    result[OWNER_KEY] = owner

    try:
        report_id = save_json_report(result)
        result["report_id"] = report_id
        result["report_url"] = f"/api/reports/{report_id}"
        print(f"✅ Analysis {analysis_id} completed with report_id: {report_id}")
    except Exception as e:
        print(f"⚠️ Failed to save report: {e}")
        result["report_save_error"] = str(e)

    return result


@router.get("/status/{task_id}")
async def get_analysis_status(
    task_id: str,
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    status = _get_owned_task(task_id, owner)

    try:
        analysis_info = _get_analysis_info_by_task(task_id)
        response = {
            "task_id": task_id,
            "status": status.get("status", "unknown"),
            "created_at": status.get("created_at"),
            "completed_at": status.get("completed_at"),
            "function": status.get("function", "unknown"),
            "progress": status.get("progress", 0),
            # The frontend reads data.error to explain failures; it was
            # never sent before, so every failure just said "Analysis failed".
            "error": status.get("error"),
        }
        if analysis_info:
            response.update(
                {
                    "analysis_id": analysis_info.get("analysis_id"),
                    "options": analysis_info.get("options"),
                }
            )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


def _has_real_ai_insights(result: Dict[str, Any]) -> bool:
    ai = result.get("ai_insights")
    return isinstance(ai, dict) and bool(ai.get("summary")) and not ai.get("fallback")


@router.get("/results/{task_id}")
async def get_analysis_results(
    task_id: str,
    include_ai: bool = Query(False),
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    status = _get_owned_task(task_id, owner)

    if status.get("status") in {"queued", "running"}:
        raise HTTPException(
            status_code=425, detail=f"Analysis task {task_id} is still processing"
        )

    try:
        stored = await task_queue.get_result(task_id, timeout=30)
    except TimeoutError:
        raise HTTPException(
            status_code=408, detail=f"Timeout waiting for results of task {task_id}"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=404, detail=TASK_GONE_DETAIL)

    if not isinstance(stored, dict):
        raise HTTPException(status_code=404, detail=f"No results found for task {task_id}")

    # Call the LLM once per task and cache it. Before, every results fetch
    # (AnalyzePage, then ResultsPage, then every refresh) made a fresh LLM
    # call of up to LLM_TIMEOUT seconds while the UI sat at 100%.
    if include_ai and settings.ENABLE_AI_INSIGHTS and not _has_real_ai_insights(stored):
        try:
            from app.services.ai.analyze_ai import enhance_with_ai

            enhanced = await enhance_with_ai(copy.deepcopy(stored))
            ai = enhanced.get("ai_insights")
            if ai:
                stored["ai_insights"] = ai
                if _has_real_ai_insights(stored) and stored.get("report_id"):
                    try:
                        save_json_report(stored, report_id=stored["report_id"])
                    except Exception as e:
                        print(f"⚠️ Could not persist AI insights: {e}")
        except Exception as e:
            print(f"⚠️ AI enhancement failed: {e}")

    result = strip_owner(stored)
    if not include_ai:
        result.pop("ai_insights", None)
    result["task_id"] = task_id
    result["retrieved_at"] = datetime.now().isoformat()
    return result


@router.get("/queue/stats")
async def get_queue_stats() -> Dict[str, Any]:
    try:
        tasks = task_queue.list_tasks()
        status_counts: Dict[str, int] = {}
        for task in tasks.values():
            s = task.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1

        running = sum(1 for t in tasks.values() if t.get("status") == "running")
        return {
            "total_tasks": len(tasks),
            "status_counts": status_counts,
            "max_workers": getattr(task_queue, "max_workers", 0),
            "active_workers": min(running, getattr(task_queue, "max_workers", 0)),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue stats: {str(e)}")


@router.get("/recent")
async def get_recent_analyses(
    limit: int = Query(10, ge=1, le=100),
    owner: str = Depends(get_owner),
) -> Dict[str, Any]:
    """The caller's own recent analyses."""
    try:
        tasks = {
            tid: t for tid, t in task_queue.list_tasks(limit=10000).items()
            if same_owner(_task_owner(t), owner)
        }
        recent_tasks = []

        sorted_tasks = sorted(
            tasks.items(),
            key=lambda x: x[1].get("created_at") or "",
            reverse=True,
        )[:limit]

        for task_id, task in sorted_tasks:
            analysis_info = _get_analysis_info_by_task(task_id)
            recent_task = {
                "task_id": task_id,
                "status": task.get("status", "unknown"),
                "created_at": task.get("created_at"),
                "completed_at": task.get("completed_at"),
                "function": task.get("function", "unknown"),
            }
            if analysis_info:
                recent_task.update(
                    {
                        "analysis_id": analysis_info.get("analysis_id"),
                        "repo_name": Path(analysis_info.get("path") or "").name,
                    }
                )
            if task.get("status") == "completed":
                recent_task["has_results"] = isinstance(task.get("result"), dict)
            recent_tasks.append(recent_task)

        return {"analyses": recent_tasks, "total": len(recent_tasks), "limit": limit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent analyses: {str(e)}")


# ── In-memory analysis metadata store ─────────────────────────────
_analysis_store: Dict[str, Dict[str, Any]] = {}
_task_to_analysis: Dict[str, str] = {}


def _store_analysis_info(analysis_id: str, info: Dict[str, Any]) -> None:
    _analysis_store[analysis_id] = info
    task_id = info.get("task_id")
    if task_id:
        _task_to_analysis[task_id] = analysis_id


def _get_analysis_info(analysis_id: str) -> Optional[Dict[str, Any]]:
    return _analysis_store.get(analysis_id)


def _get_analysis_info_by_task(task_id: str) -> Optional[Dict[str, Any]]:
    analysis_id = _task_to_analysis.get(task_id)
    if analysis_id:
        return _analysis_store.get(analysis_id)
    return None


def _estimate_analysis_time(repo_path: Path, options: Dict[str, Any]) -> int:
    try:
        file_count = 0
        for _root, dirs, files in os.walk(repo_path):
            dirs[:] = [
                d for d in dirs
                if d not in {".git", "__pycache__", "node_modules", "venv", ".venv"}
            ]
            file_count += len(files)

        base_time_per_file = 0.1
        depth_multiplier = {"quick": 0.5, "standard": 1.0, "full": 2.0}.get(
            options.get("depth", "standard"), 1.0
        )
        if options.get("include_security", True):
            base_time_per_file *= 1.5
        if options.get("include_complexity", True):
            base_time_per_file *= 1.3

        estimated_seconds = int(file_count * base_time_per_file * depth_multiplier)
        return max(10, min(estimated_seconds, 300))
    except Exception as e:
        print(f"⚠️ Error estimating analysis time: {e}")
        return 60