"""
Analysis endpoints.
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.core.config import settings
from app.services.export.json import save_json_report
from app.workers.analyze_task import analyze_repo
from app.workers.task_queue import task_queue

router = APIRouter(prefix="/analyze")


@router.post("", response_model=Dict[str, Any])
async def analyze_repository(
    path: str,
    background_tasks: BackgroundTasks,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        repo_path = Path(path).resolve()

        if not repo_path.exists():
            raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")
        if not repo_path.is_dir():
            raise HTTPException(
                status_code=400, detail=f"Path is not a directory: {path}"
            )

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
        )

        print(f"✅ Task created with ID: {task_id}")

        analysis_info = {
            "analysis_id": analysis_id,
            "task_id": task_id,
            "path": str(repo_path),
            "options": options,
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
        raise HTTPException(
            status_code=500, detail=f"Failed to start analysis: {str(e)}"
        )


def _run_analysis_with_options(
    path: str, options: Dict[str, Any], analysis_id: str
) -> Dict[str, Any]:
    try:
        print(f"🏃 Running analysis {analysis_id} for path: {path}")
        result = analyze_repo(path)

        if not isinstance(result, dict):
            print(f"⚠️ analyze_repo returned non-dict: {type(result)}")
            result = {
                "raw_result": str(result) if result else "Empty result",
                "analysis_id": analysis_id,
                "path": path,
                "status": "completed",
            }
        else:
            result["analysis_id"] = analysis_id
            result["options_used"] = options
            result["status"] = "completed"
            result["completed_at"] = datetime.now().isoformat()

        try:
            if isinstance(result, dict) and result.get("status") == "completed":
                report_id = save_json_report(result)
                result["report_id"] = report_id
                result["report_url"] = f"/api/reports/{report_id}"
                print(
                    f"✅ Analysis {analysis_id} completed with report_id: {report_id}"
                )
            else:
                print(f"⚠️ Analysis {analysis_id} status is not 'completed'")
        except Exception as e:
            print(f"⚠️ Failed to save report: {e}")
            result["report_save_error"] = str(e)

        return result
    except Exception as e:
        print(f"❌ Analysis {analysis_id} failed: {str(e)}")
        return {
            "analysis_id": analysis_id,
            "path": path,
            "error": str(e),
            "status": "failed",
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/status/{task_id}")
async def get_analysis_status(task_id: str) -> Dict[str, Any]:
    try:
        status = task_queue.get_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        analysis_info = _get_analysis_info_by_task(task_id)

        response = {
            "task_id": task_id,
            "status": status.get("status", "unknown"),
            "created_at": status.get("created_at"),
            "completed_at": status.get("completed_at"),
            "function": status.get("function", "unknown"),
            "progress": status.get("progress", 0),
        }
        if analysis_info:
            response.update(
                {
                    "analysis_id": analysis_info.get("analysis_id"),
                    "path": analysis_info.get("path"),
                    "options": analysis_info.get("options"),
                }
            )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get status: {str(e)}"
        )


@router.get("/results/{task_id}")
async def get_analysis_results(
    task_id: str,
    include_ai: bool = Query(False),
) -> Dict[str, Any]:
    try:
        status = task_queue.get_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        if status.get("status") == "running":
            raise HTTPException(
                status_code=425,
                detail=f"Analysis task {task_id} is still processing",
            )

        result = await task_queue.get_result(task_id, timeout=30)
        if result is None:
            raise HTTPException(
                status_code=404, detail=f"No results found for task {task_id}"
            )

        if include_ai:
            try:
                from app.services.ai.analyze_ai import enhance_with_ai

                if settings.ENABLE_AI_INSIGHTS:
                    result = await enhance_with_ai(result)
            except ImportError as e:
                print(f"⚠️ AI import failed: {e}")
            except Exception as e:
                print(f"⚠️ AI enhancement failed: {e}")

        if not isinstance(result, dict):
            result = {
                "data": str(result) if result else "Empty result",
                "status": "completed",
                "task_id": task_id,
                "raw_result_type": str(type(result)),
            }

        result["task_id"] = task_id
        result["retrieved_at"] = datetime.now().isoformat()
        return result
    except TimeoutError:
        raise HTTPException(
            status_code=408, detail=f"Timeout waiting for results of task {task_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get results: {str(e)}"
        )


@router.get("/queue/stats")
async def get_queue_stats() -> Dict[str, Any]:
    try:
        tasks = task_queue.list_tasks()
        status_counts: Dict[str, int] = {}
        for task in tasks.values():
            status = task.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        running = sum(1 for t in tasks.values() if t.get("status") == "running")
        return {
            "total_tasks": len(tasks),
            "status_counts": status_counts,
            "max_workers": getattr(task_queue, "max_workers", 0),
            "active_workers": min(running, getattr(task_queue, "max_workers", 0)),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get queue stats: {str(e)}"
        )


@router.get("/recent")
async def get_recent_analyses(
    limit: int = Query(10, ge=1, le=100),
) -> Dict[str, Any]:
    try:
        tasks = task_queue.list_tasks()
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
                        "path": analysis_info.get("path"),
                    }
                )
            if task.get("status") == "completed":
                try:
                    result = await task_queue.get_result(task_id, timeout=1)
                    if isinstance(result, dict):
                        recent_task["has_results"] = True
                        recent_task["result_status"] = result.get("status", "unknown")
                except Exception:
                    pass
            recent_tasks.append(recent_task)

        return {"analyses": recent_tasks, "total": len(recent_tasks), "limit": limit}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get recent analyses: {str(e)}"
        )


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
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [
                d
                for d in dirs
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