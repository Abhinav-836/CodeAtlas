"""
Robust task queue for background processing with persistence and monitoring.
"""
import asyncio
import json
import logging
import uuid
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Callable, Any, Dict, Optional, List, Union, Tuple
import pickle

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskQueue:
    """
    Advanced task queue with persistence, monitoring, and recovery.
    
    Features:
    - Persistent storage of task results
    - Task prioritization
    - Automatic retry on failure
    - Progress tracking
    - Resource limits
    - Task dependencies
    
    Example:
        >>> queue = TaskQueue(max_workers=4, persist_results=True)
        >>> task_id = await queue.enqueue(analyze_function, "path/to/repo", priority=1)
        >>> result = await queue.get_result(task_id, timeout=300)
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        persist_results: bool = True,
        results_dir: str = "storage/task_results",
        max_queue_size: int = 1000,
        default_timeout: int = 300,
        cleanup_interval: int = 3600,  # 1 hour
    ):
        """
        Initialize task queue.
        
        Args:
            max_workers: Maximum number of worker threads
            persist_results: Whether to persist task results to disk
            results_dir: Directory for persisted results
            max_queue_size: Maximum number of tasks in queue
            default_timeout: Default timeout for tasks in seconds
            cleanup_interval: Interval for cleaning old tasks in seconds
        """
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="task_queue_worker"
        )
        
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_queue = deque()
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.default_timeout = default_timeout
        self.persist_results = persist_results
        self.lock = Lock()
        
        # Setup persistence
        if persist_results:
            self.results_dir = Path(results_dir)
            self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup cleanup task
        self.cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "tasks_completed": 0,
            "average_duration": 0,
            "peak_queue_size": 0,
        }
        
        logger.info(f"TaskQueue initialized with {max_workers} workers")
    
    async def start(self):
        """Start the task queue with background cleanup."""
        if self.cleanup_interval > 0:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def stop(self):
        """Stop the task queue gracefully."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.executor.shutdown(wait=True)
        logger.info("TaskQueue stopped")
    
    async def enqueue(
        self,
        func: Callable,
        *args,
        priority: int = 5,  # 1=highest, 10=lowest
        timeout: Optional[int] = None,
        retry_count: int = 0,
        task_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """
        Enqueue a task for background execution.
        
        Args:
            func: Function to execute
            *args: Function arguments
            priority: Task priority (1-10, 1 is highest)
            timeout: Task timeout in seconds
            retry_count: Number of retries on failure
            task_name: Human-readable task name
            metadata: Additional task metadata
            **kwargs: Function keyword arguments
            
        Returns:
            Task ID for tracking
            
        Raises:
            RuntimeError: If queue is full
        """
        with self.lock:
            if len(self.task_queue) >= self.max_queue_size:
                raise RuntimeError(f"Task queue is full (max: {self.max_queue_size})")
            
            task_id = str(uuid.uuid4())
            created_at = datetime.now()
            
            # Store task info
            task_info = {
                "id": task_id,
                "status": TaskStatus.QUEUED.value,
                "created_at": created_at.isoformat(),
                "function": func.__name__ if hasattr(func, '__name__') else str(func),
                "function_module": func.__module__ if hasattr(func, '__module__') else "unknown",
                "priority": max(1, min(10, priority)),
                "timeout": timeout or self.default_timeout,
                "retry_count": retry_count,
                "retries_left": retry_count,
                "task_name": task_name or func.__name__,
                "metadata": metadata or {},
                "progress": 0.0,
                "attempts": 0,
                "args": args,
                "kwargs": kwargs,
            }
            
            self.tasks[task_id] = task_info
            
            # Add to priority queue (lower number = higher priority)
            self.task_queue.append((priority, task_id))
            self.task_queue = deque(sorted(self.task_queue, key=lambda x: x[0]))
            
            # Update stats
            self.stats["peak_queue_size"] = max(
                self.stats["peak_queue_size"],
                len(self.task_queue)
            )
        
        logger.info(f"Task {task_id} queued: {task_name or func.__name__}")
        
        # Start processing if not at max workers
        asyncio.create_task(self._process_queue())
        
        return task_id
    
    async def _process_queue(self):
        """Process tasks from the queue."""
        while True:
            with self.lock:
                if not self.task_queue:
                    break
                
                # Get next task based on priority
                priority, task_id = self.task_queue.popleft()
                
                if task_id not in self.tasks:
                    continue
                
                task_info = self.tasks[task_id]
                if task_info["status"] != TaskStatus.QUEUED.value:
                    continue
                
                # Mark as running
                task_info["status"] = TaskStatus.RUNNING.value
                task_info["started_at"] = datetime.now().isoformat()
                task_info["attempts"] += 1
            
            # Execute task
            await self._execute_task(task_id)
    
    async def _execute_task(self, task_id: str):
        """Execute a task in the thread pool."""
        task_info = self.tasks.get(task_id)
        if not task_info:
            return
        
        func_name = task_info["function"]
        args = task_info["args"]
        kwargs = task_info["kwargs"]
        timeout = task_info["timeout"]
        
        logger.info(f"Executing task {task_id}: {func_name}")
        
        try:
            # Import and get function
            module_name = task_info["function_module"]
            if module_name != "unknown":
                try:
                    import importlib
                    module = importlib.import_module(module_name)
                    func = getattr(module, func_name, None)
                except (ImportError, AttributeError):
                    func = None
            else:
                func = None
            
            # If we couldn't get the function, skip
            if not func:
                task_info["status"] = TaskStatus.FAILED.value
                task_info["error"] = f"Function {func_name} not found"
                task_info["completed_at"] = datetime.now().isoformat()
                return
            
            # Execute in thread pool with timeout
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                self.executor,
                self._safe_execute,
                task_id,
                func,
                *args,
                **kwargs
            )
            
            # Wait for result with timeout
            try:
                result = await asyncio.wait_for(future, timeout=timeout)
                
                # Task completed successfully
                task_info["status"] = TaskStatus.COMPLETED.value
                task_info["result"] = result
                task_info["progress"] = 100.0
                task_info["completed_at"] = datetime.now().isoformat()
                
                # Update stats
                self.stats["tasks_processed"] += 1
                self.stats["tasks_completed"] += 1
                
                # Calculate duration
                if "started_at" in task_info:
                    started = datetime.fromisoformat(task_info["started_at"])
                    completed = datetime.fromisoformat(task_info["completed_at"])
                    duration = (completed - started).total_seconds()
                    task_info["duration_seconds"] = duration
                    
                    # Update average duration
                    if self.stats["tasks_completed"] > 0:
                        old_avg = self.stats["average_duration"]
                        new_avg = (old_avg * (self.stats["tasks_completed"] - 1) + duration) / self.stats["tasks_completed"]
                        self.stats["average_duration"] = new_avg
                
                # Persist result if enabled
                if self.persist_results:
                    self._persist_result(task_id, task_info)
                
                logger.info(f"Task {task_id} completed successfully")
                
            except asyncio.TimeoutError:
                task_info["status"] = TaskStatus.TIMEOUT.value
                task_info["error"] = f"Task timed out after {timeout} seconds"
                task_info["completed_at"] = datetime.now().isoformat()
                self.stats["tasks_failed"] += 1
                logger.warning(f"Task {task_id} timed out")
        
        except Exception as e:
            task_info["status"] = TaskStatus.FAILED.value
            task_info["error"] = str(e)
            task_info["completed_at"] = datetime.now().isoformat()
            self.stats["tasks_failed"] += 1
            logger.error(f"Task {task_id} failed: {e}")
            
            # Retry if configured
            if task_info["retries_left"] > 0:
                task_info["retries_left"] -= 1
                task_info["status"] = TaskStatus.QUEUED.value
                with self.lock:
                    self.task_queue.append((task_info["priority"], task_id))
                logger.info(f"Task {task_id} queued for retry ({task_info['retries_left']} left)")
    
    def _safe_execute(self, task_id: str, func: Callable, *args, **kwargs) -> Any:
        """Safely execute a function with progress tracking."""
        try:
            # If function accepts task_id, pass it
            import inspect
            sig = inspect.signature(func)
            params = sig.parameters
            
            if 'task_id' in params:
                kwargs['task_id'] = task_id
            
            # Execute function
            return func(*args, **kwargs)
        
        except Exception as e:
            logger.error(f"Error in task {task_id}: {e}")
            raise
    
    async def get_result(self, task_id: str, timeout: Optional[int] = None) -> Any:
        """
        Get task result with timeout.
        
        Args:
            task_id: Task ID to check
            timeout: Timeout in seconds (uses task timeout if None)
            
        Returns:
            Task result
            
        Raises:
            ValueError: Task not found
            TimeoutError: Task timed out
            RuntimeError: Task failed
        """
        if task_id not in self.tasks:
            # Try to load from persistence
            if self.persist_results:
                task_info = self._load_result(task_id)
                if task_info:
                    if task_info["status"] == TaskStatus.COMPLETED.value:
                        return task_info.get("result")
                    elif task_info["status"] == TaskStatus.FAILED.value:
                        raise RuntimeError(f"Task failed: {task_info.get('error', 'Unknown error')}")
            
            raise ValueError(f"Task {task_id} not found")
        
        task_info = self.tasks[task_id]
        
        # Wait for task completion
        start_time = time.time()
        timeout = timeout or task_info["timeout"]
        
        while True:
            status = task_info["status"]
            
            if status == TaskStatus.COMPLETED.value:
                return task_info.get("result")
            
            elif status == TaskStatus.FAILED.value:
                error = task_info.get("error", "Unknown error")
                raise RuntimeError(f"Task failed: {error}")
            
            elif status == TaskStatus.TIMEOUT.value:
                raise TimeoutError(f"Task timed out")
            
            elif status == TaskStatus.CANCELLED.value:
                raise RuntimeError("Task was cancelled")
            
            # Check timeout
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for task {task_id}")
            
            # Wait before checking again
            await asyncio.sleep(0.5)
    
    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status.
        
        Args:
            task_id: Task ID to check
            
        Returns:
            Task status dictionary or None if not found
        """
        if task_id in self.tasks:
            return self.tasks[task_id].copy()
        
        # Try to load from persistence
        if self.persist_results:
            return self._load_result(task_id)
        
        return None
    
    def update_progress(self, task_id: str, progress: float, message: Optional[str] = None):
        """
        Update task progress.
        
        Args:
            task_id: Task ID
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        if task_id in self.tasks:
            self.tasks[task_id]["progress"] = max(0.0, min(100.0, progress))
            if message:
                self.tasks[task_id]["progress_message"] = message
    
    def list_tasks(
        self,
        status_filter: Optional[Union[str, List[str]]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Dict[str, Any]]:
        """
        List all tasks, optionally filtered by status.
        
        Args:
            status_filter: Filter by status or list of statuses
            limit: Maximum number of tasks to return
            offset: Pagination offset
            
        Returns:
            Dictionary of tasks
        """
        filtered_tasks = {}
        
        # Convert single status to list
        if status_filter and isinstance(status_filter, str):
            status_filter = [status_filter]
        
        for task_id, task in self.tasks.items():
            if status_filter and task.get("status") not in status_filter:
                continue
            
            # Apply pagination
            if offset > 0:
                offset -= 1
                continue
            
            if limit <= 0:
                break
            
            filtered_tasks[task_id] = task.copy()
            limit -= 1
        
        return filtered_tasks
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            True if cancelled, False otherwise
        """
        if task_id not in self.tasks:
            return False
        
        task_info = self.tasks[task_id]
        
        # Can only cancel queued or running tasks
        if task_info["status"] not in [TaskStatus.QUEUED.value, TaskStatus.RUNNING.value]:
            return False
        
        task_info["status"] = TaskStatus.CANCELLED.value
        task_info["completed_at"] = datetime.now().isoformat()
        
        # Remove from queue if queued
        with self.lock:
            self.task_queue = deque([t for t in self.task_queue if t[1] != task_id])
        
        logger.info(f"Task {task_id} cancelled")
        return True
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self.lock:
            queue_size = len(self.task_queue)
        
        running_tasks = len([
            t for t in self.tasks.values()
            if t.get("status") == TaskStatus.RUNNING.value
        ])
        
        return {
            **self.stats,
            "current_queue_size": queue_size,
            "running_tasks": running_tasks,
            "total_tasks": len(self.tasks),
            "available_workers": self.max_workers - running_tasks,
        }
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        Clean up old completed tasks.
        
        Args:
            max_age_hours: Maximum age in hours to keep tasks
            
        Returns:
            Number of tasks cleaned up
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        tasks_to_remove = []
        
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
        
        # Also clean up persisted results
        if self.persist_results:
            self._cleanup_persisted_results(cutoff)
        
        logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
        return len(tasks_to_remove)
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old tasks."""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_old_tasks()
        except asyncio.CancelledError:
            pass
    
    def _persist_result(self, task_id: str, task_info: Dict[str, Any]):
        """Persist task result to disk."""
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.results_dir / f"{task_id}_{timestamp}.json"
            
            # Make task info JSON serializable
            serializable_info = {}
            for key, value in task_info.items():
                if key in ["args", "kwargs", "result"]:
                    # Serialize complex objects
                    try:
                        serializable_info[key] = pickle.dumps(value).hex()
                    except Exception:
                        serializable_info[key] = str(value)
                else:
                    serializable_info[key] = value
            
            # Write to file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_info, f, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Failed to persist task {task_id}: {e}")
    
    def _load_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Load task result from disk."""
        try:
            # Find the latest result file for this task
            result_files = list(self.results_dir.glob(f"{task_id}_*.json"))
            if not result_files:
                return None
            
            # Get the most recent file
            latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                task_info = json.load(f)
            
            # Deserialize complex objects
            for key in ["args", "kwargs", "result"]:
                if key in task_info and isinstance(task_info[key], str):
                    try:
                        task_info[key] = pickle.loads(bytes.fromhex(task_info[key]))
                    except Exception:
                        # If deserialization fails, keep as string
                        pass
            
            return task_info
            
        except Exception as e:
            logger.error(f"Failed to load task {task_id}: {e}")
            return None
    
    def _cleanup_persisted_results(self, cutoff: datetime):
        """Clean up old persisted results."""
        try:
            for result_file in self.results_dir.glob("*.json"):
                try:
                    file_time = datetime.fromtimestamp(result_file.stat().st_mtime)
                    if file_time < cutoff:
                        result_file.unlink()
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Failed to cleanup persisted results: {e}")


# Global task queue instance
task_queue = TaskQueue(max_workers=4, persist_results=True)