"""
Robust task queue for background processing with persistence and monitoring.
"""
import asyncio
import importlib
import inspect
import json
import logging
import pickle
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskQueue:
    """
    Advanced task queue with persistence, monitoring, and recovery.
    """

    def __init__(
        self,
        max_workers: int = 4,
        persist_results: bool = True,
        results_dir: str = "storage/task_results",
        max_queue_size: int = 1000,
        default_timeout: int = 300,
        cleanup_interval: int = 3600,
    ) -> None:
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="task_queue_worker"
        )
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_queue: deque = deque()
        self._func_refs: Dict[str, Callable] = {}
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.default_timeout = default_timeout
        self.persist_results = persist_results
        self.lock = Lock()

        if persist_results:
            self.results_dir = Path(results_dir)
            self.results_dir.mkdir(parents=True, exist_ok=True)

        self.cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None

        self.stats = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "tasks_completed": 0,
            "average_duration": 0.0,
            "peak_queue_size": 0,
        }

        logger.info("TaskQueue initialized with %s workers", max_workers)

    async def start(self) -> None:
        if self.cleanup_interval > 0 and self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def stop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        self.executor.shutdown(wait=True)
        logger.info("TaskQueue stopped")

    async def enqueue(
        self,
        func: Callable,
        *args,
        priority: int = 5,
        timeout: Optional[int] = None,
        retry_count: int = 0,
        task_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        with self.lock:
            if len(self.task_queue) >= self.max_queue_size:
                raise RuntimeError(f"Task queue is full (max: {self.max_queue_size})")

            task_id = str(uuid.uuid4())
            created_at = datetime.now()

            task_info = {
                "id": task_id,
                "status": TaskStatus.QUEUED.value,
                "created_at": created_at.isoformat(),
                "function": getattr(func, "__name__", str(func)),
                "function_module": getattr(func, "__module__", "unknown"),
                "priority": max(1, min(10, priority)),
                "timeout": timeout or self.default_timeout,
                "retry_count": retry_count,
                "retries_left": retry_count,
                "task_name": task_name or getattr(func, "__name__", "task"),
                "metadata": metadata or {},
                "progress": 0.0,
                "attempts": 0,
                "args": args,
                "kwargs": kwargs,
            }
            self.tasks[task_id] = task_info
            self._func_refs[task_id] = func

            self.task_queue.append((priority, task_id))
            self.task_queue = deque(sorted(self.task_queue, key=lambda x: x[0]))

            self.stats["peak_queue_size"] = max(
                self.stats["peak_queue_size"], len(self.task_queue)
            )

        logger.info("Task %s queued: %s", task_id, task_info["task_name"])
        asyncio.create_task(self._process_queue())
        return task_id

    async def _process_queue(self) -> None:
        while True:
            with self.lock:
                if not self.task_queue:
                    break

                _, task_id = self.task_queue.popleft()
                if task_id not in self.tasks:
                    continue

                task_info = self.tasks[task_id]
                if task_info["status"] != TaskStatus.QUEUED.value:
                    continue

                task_info["status"] = TaskStatus.RUNNING.value
                task_info["started_at"] = datetime.now().isoformat()
                task_info["attempts"] += 1

            await self._execute_task(task_id)

    async def _execute_task(self, task_id: str) -> None:
        task_info = self.tasks.get(task_id)
        if not task_info:
            return

        func_name = task_info["function"]
        args = task_info["args"]
        kwargs = task_info["kwargs"]
        timeout = task_info["timeout"]

        logger.info("Executing task %s: %s", task_id, func_name)

        try:
            func = self._func_refs.get(task_id)

            # Fallback only for tasks rehydrated after a process restart.
            if func is None:
                module_name = task_info["function_module"]
                if module_name != "unknown":
                    try:
                        module = importlib.import_module(module_name)
                        func = getattr(module, func_name, None)
                    except (ImportError, AttributeError):
                        func = None

            if not func:
                task_info["status"] = TaskStatus.FAILED.value
                task_info["error"] = f"Function {func_name} not found"
                task_info["completed_at"] = datetime.now().isoformat()
                return

            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                self.executor, self._safe_execute, task_id, func, *args, **kwargs
            )

            try:
                result = await asyncio.wait_for(future, timeout=timeout)

                task_info["status"] = TaskStatus.COMPLETED.value
                task_info["result"] = result
                task_info["progress"] = 100.0
                task_info["completed_at"] = datetime.now().isoformat()

                self.stats["tasks_processed"] += 1
                self.stats["tasks_completed"] += 1

                if "started_at" in task_info:
                    started = datetime.fromisoformat(task_info["started_at"])
                    completed = datetime.fromisoformat(task_info["completed_at"])
                    duration = (completed - started).total_seconds()
                    task_info["duration_seconds"] = duration

                    completed_count = self.stats["tasks_completed"]
                    if completed_count > 0:
                        old_avg = self.stats["average_duration"]
                        self.stats["average_duration"] = (
                            old_avg * (completed_count - 1) + duration
                        ) / completed_count

                if self.persist_results:
                    self._persist_result(task_id, task_info)

                logger.info("Task %s completed successfully", task_id)

            except asyncio.TimeoutError:
                task_info["status"] = TaskStatus.TIMEOUT.value
                task_info["error"] = f"Task timed out after {timeout} seconds"
                task_info["completed_at"] = datetime.now().isoformat()
                self.stats["tasks_failed"] += 1
                logger.warning("Task %s timed out", task_id)

        except Exception as e:
            task_info["status"] = TaskStatus.FAILED.value
            task_info["error"] = str(e)
            task_info["completed_at"] = datetime.now().isoformat()
            self.stats["tasks_failed"] += 1
            logger.error("Task %s failed: %s", task_id, e)

            if task_info["retries_left"] > 0:
                task_info["retries_left"] -= 1
                task_info["status"] = TaskStatus.QUEUED.value
                with self.lock:
                    self.task_queue.append((task_info["priority"], task_id))
                logger.info(
                    "Task %s queued for retry (%s left)",
                    task_id, task_info["retries_left"],
                )

    def _safe_execute(self, task_id: str, func: Callable, *args, **kwargs) -> Any:
        try:
            sig = inspect.signature(func)
            if "task_id" in sig.parameters:
                kwargs["task_id"] = task_id
            return func(*args, **kwargs)
        except Exception as e:
            logger.error("Error in task %s: %s", task_id, e)
            raise

    async def get_result(self, task_id: str, timeout: Optional[int] = None) -> Any:
        if task_id not in self.tasks:
            if self.persist_results:
                task_info = self._load_result(task_id)
                if task_info:
                    if task_info["status"] == TaskStatus.COMPLETED.value:
                        return task_info.get("result")
                    if task_info["status"] == TaskStatus.FAILED.value:
                        raise RuntimeError(
                            f"Task failed: {task_info.get('error', 'Unknown error')}"
                        )
            raise ValueError(f"Task {task_id} not found")

        task_info = self.tasks[task_id]
        start_time = time.time()
        timeout = timeout or task_info["timeout"]

        while True:
            status = task_info["status"]

            if status == TaskStatus.COMPLETED.value:
                return task_info.get("result")
            if status == TaskStatus.FAILED.value:
                raise RuntimeError(f"Task failed: {task_info.get('error', 'Unknown error')}")
            if status == TaskStatus.TIMEOUT.value:
                raise TimeoutError("Task timed out")
            if status == TaskStatus.CANCELLED.value:
                raise RuntimeError("Task was cancelled")

            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for task {task_id}")

            await asyncio.sleep(0.5)

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        if task_id in self.tasks:
            return self.tasks[task_id].copy()
        if self.persist_results:
            return self._load_result(task_id)
        return None

    def update_progress(self, task_id: str, progress: float, message: Optional[str] = None) -> None:
        if task_id in self.tasks:
            self.tasks[task_id]["progress"] = max(0.0, min(100.0, progress))
            if message:
                self.tasks[task_id]["progress_message"] = message

    def list_tasks(
        self,
        status_filter: Optional[Union[str, List[str]]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Dict[str, Any]]:
        filtered_tasks: Dict[str, Dict[str, Any]] = {}

        if isinstance(status_filter, str):
            status_filter = [status_filter]

        for task_id, task in self.tasks.items():
            if status_filter and task.get("status") not in status_filter:
                continue
            if offset > 0:
                offset -= 1
                continue
            if limit <= 0:
                break
            filtered_tasks[task_id] = task.copy()
            limit -= 1

        return filtered_tasks

    def cancel_task(self, task_id: str) -> bool:
        if task_id not in self.tasks:
            return False

        task_info = self.tasks[task_id]
        if task_info["status"] not in {TaskStatus.QUEUED.value, TaskStatus.RUNNING.value}:
            return False

        task_info["status"] = TaskStatus.CANCELLED.value
        task_info["completed_at"] = datetime.now().isoformat()

        with self.lock:
            self.task_queue = deque([t for t in self.task_queue if t[1] != task_id])

        logger.info("Task %s cancelled", task_id)
        return True

    def get_queue_stats(self) -> Dict[str, Any]:
        with self.lock:
            queue_size = len(self.task_queue)

        running_tasks = sum(
            1 for t in self.tasks.values() if t.get("status") == TaskStatus.RUNNING.value
        )

        return {
            **self.stats,
            "current_queue_size": queue_size,
            "running_tasks": running_tasks,
            "total_tasks": len(self.tasks),
            "available_workers": max(0, self.max_workers - running_tasks),
        }

    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        tasks_to_remove: List[str] = []

        for task_id, task in self.tasks.items():
            if "completed_at" in task:
                try:
                    completed_time = datetime.fromisoformat(task["completed_at"])
                    if completed_time < cutoff:
                        tasks_to_remove.append(task_id)
                except (ValueError, KeyError):
                    continue

        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            self._func_refs.pop(task_id, None)

        if self.persist_results:
            self._cleanup_persisted_results(cutoff)

        logger.info("Cleaned up %s old tasks", len(tasks_to_remove))
        return len(tasks_to_remove)

    async def _periodic_cleanup(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_old_tasks()
        except asyncio.CancelledError:
            pass

    # ── Persistence ────────────────────────────────────────────────
    def _persist_result(self, task_id: str, task_info: Dict[str, Any]) -> None:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.results_dir / f"{task_id}_{timestamp}.json"

            serializable_info: Dict[str, Any] = {}
            for key, value in task_info.items():
                if key in {"args", "kwargs", "result"}:
                    try:
                        serializable_info[key] = pickle.dumps(value).hex()
                    except Exception:
                        serializable_info[key] = str(value)
                else:
                    serializable_info[key] = value

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(serializable_info, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to persist task %s: %s", task_id, e)

    def _load_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        try:
            result_files = list(self.results_dir.glob(f"{task_id}_*.json"))
            if not result_files:
                return None

            latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
            with open(latest_file, "r", encoding="utf-8") as f:
                task_info = json.load(f)

            for key in ["args", "kwargs", "result"]:
                if key in task_info and isinstance(task_info[key], str):
                    try:
                        task_info[key] = pickle.loads(bytes.fromhex(task_info[key]))
                    except Exception:
                        pass

            return task_info
        except Exception as e:
            logger.error("Failed to load task %s: %s", task_id, e)
            return None

    def _cleanup_persisted_results(self, cutoff: datetime) -> None:
        try:
            for result_file in self.results_dir.glob("*.json"):
                try:
                    file_time = datetime.fromtimestamp(result_file.stat().st_mtime)
                    if file_time < cutoff:
                        result_file.unlink()
                except Exception:
                    continue
        except Exception as e:
            logger.error("Failed to cleanup persisted results: %s", e)


# Global instance
task_queue = TaskQueue(max_workers=4, persist_results=True)