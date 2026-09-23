"""
FastAPI application entry point - CodeAtlas API
"""
import asyncio
import logging
import time
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException as StarletteHTTPException

# ✅ Single source of truth for settings
from app.core.config import settings

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# -------------------------------------------------
# File utilities (inlined)
# -------------------------------------------------
def ensure_dir(directory: str) -> str:
    os.makedirs(directory, exist_ok=True)
    return directory


def cleanup_old_files(directory: str, max_age_hours: int = 24) -> None:
    from pathlib import Path

    dir_path = Path(directory)
    if not dir_path.exists():
        return

    cutoff_time = time.time() - (max_age_hours * 3600)
    for file_path in dir_path.rglob("*"):
        if file_path.is_file():
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
            except (OSError, PermissionError):
                pass


# -------------------------------------------------
# WebSocket Connection Manager
# -------------------------------------------------
class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, task_id: str) -> None:
        await websocket.accept()
        self.active_connections[task_id] = websocket
        logger.info("WebSocket connected for task %s", task_id)

    def disconnect(self, task_id: str) -> None:
        if task_id in self.active_connections:
            del self.active_connections[task_id]
            logger.info("WebSocket disconnected for task %s", task_id)


ws_manager = ConnectionManager()


# -------------------------------------------------
# Optional imports with fallbacks
# -------------------------------------------------
try:
    from app.db.session import init_db, close_db, check_db_health  # noqa: F401
    logger.info("✅ Using database functions from app.db.session")
except ImportError as e:
    logger.warning("⚠️ Database module not found (%s), using stubs", e)

    async def init_db() -> None:  # type: ignore
        logger.info("Database initialization skipped")

    async def close_db() -> None:  # type: ignore
        pass

    async def check_db_health() -> Dict[str, Any]:  # type: ignore
        return {"status": "unknown", "message": "Database module not loaded"}


try:
    from app.workers.task_queue import task_queue
    logger.info("✅ Using real task queue")
except ImportError as e:
    logger.warning("⚠️ Real task queue not found (%s), using simple fallback", e)

    class SimpleTaskQueue:
        def __init__(self) -> None:
            self.tasks: Dict[str, Dict[str, Any]] = {}
            self.results: Dict[str, Any] = {}
            self._running = False

        async def start(self) -> None:
            self._running = True
            logger.info("Simple task queue started")

        async def stop(self) -> None:
            self._running = False
            logger.info("Simple task queue stopped")

        async def enqueue(self, func, *args, **kwargs) -> str:
            import uuid
            task_id = f"task_{uuid.uuid4().hex[:10]}"
            self.tasks[task_id] = {
                "task_id": task_id,
                "function": getattr(func, "__name__", str(func)),
                "status": "queued",
                "created_at": time.time(),
                "progress": 0,
            }
            asyncio.create_task(self._execute_task(task_id, func, *args, **kwargs))
            return task_id

        async def _execute_task(self, task_id, func, *args, **kwargs) -> None:
            try:
                self.tasks[task_id]["status"] = "running"
                self.tasks[task_id]["started_at"] = time.time()

                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result

                self.tasks[task_id]["status"] = "completed"
                self.tasks[task_id]["completed_at"] = time.time()
                self.tasks[task_id]["progress"] = 100
                self.results[task_id] = result
            except Exception as e:
                self.tasks[task_id]["status"] = "failed"
                self.tasks[task_id]["error"] = str(e)
                self.tasks[task_id]["completed_at"] = time.time()
                logger.error("Task %s failed: %s", task_id, e)

        def get_status(self, task_id: str):
            return self.tasks.get(task_id)

        async def get_result(self, task_id: str, timeout: int = 30) -> Any:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if task_id in self.results:
                    return self.results[task_id]
                await asyncio.sleep(0.1)

            if task_id in self.tasks and self.tasks[task_id]["status"] == "completed":
                await asyncio.sleep(0.1)
                if task_id in self.results:
                    return self.results[task_id]

            raise TimeoutError(f"Timeout waiting for result of task {task_id}")

        def list_tasks(self):
            return self.tasks.copy()

    task_queue = SimpleTaskQueue()  # type: ignore


# -------------------------------------------------
# Router imports (cleaned up — no dead code)
# -------------------------------------------------
def import_router(router_name: str):
    """Import a single router dynamically, returning None on failure."""
    try:
        if router_name == "analyze":
            from app.api.routes.analyze import router
        elif router_name == "upload":
            from app.api.routes.upload import router
        elif router_name == "reports":
            from app.api.routes.reports import router
        elif router_name == "health":
            from app.api.routes.health import router
        elif router_name == "ai":
            from app.api.routes.ai import router
        elif router_name == "auth":
            from app.api.routes.auth import router
        elif router_name == "webhooks":
            from app.api.routes.webhooks import router
        elif router_name == "admin":
            from app.api.routes.admin import router
        else:
            logger.warning("Unknown router requested: %s", router_name)
            return None

        logger.info("✅ Imported router: %s", router_name)
        return router
    except ImportError as e:
        if router_name not in {"admin"} or settings.DEBUG:
            logger.warning("⚠️ Could not import router '%s': %s", router_name, e)
        return None
    except Exception as e:
        logger.error("❌ Error importing router '%s': %s", router_name, e)
        return None


routers: Dict[str, Any] = {}
router_names = ["health", "analyze", "upload", "reports", "auth", "webhooks", "ai"]
if settings.DEBUG:
    router_names.append("admin")

for name in router_names:
    r = import_router(name)
    if r:
        routers[name] = r


# -------------------------------------------------
# Lifespan
# -------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_time = time.time()
    logger.info("🚀 Starting CodeAtlas API v%s", settings.API_VERSION)

    try:
        required_dirs = [
            settings.UPLOAD_DIR,
            settings.REPORT_DIR,
            settings.EXPORT_DIR,
            "storage",
            "storage/tmp",
            "storage/logs",
            "storage/backups",
            "storage/task_results",
            "storage/repos",
        ]
        for directory in required_dirs:
            try:
                ensure_dir(directory)
                logger.debug("✅ Directory ensured: %s", directory)
            except Exception as e:
                logger.error("❌ Failed to create directory %s: %s", directory, e)
                if not settings.DEBUG:
                    raise

        try:
            await init_db()
            logger.info("✅ Database initialized")
        except Exception as e:
            logger.error("❌ Database initialization failed: %s", e)

        try:
            await task_queue.start()
            logger.info("✅ Task queue started")
        except Exception as e:
            logger.error("❌ Task queue failed to start: %s", e)

        if getattr(settings, "CLEANUP_ON_STARTUP", True):
            try:
                cleanup_old_files(settings.UPLOAD_DIR, max_age_hours=24)
                cleanup_old_files("storage/tmp", max_age_hours=1)
                cleanup_old_files("storage/task_results", max_age_hours=168)
                logger.info("✅ Old files cleaned up")
            except Exception as e:
                logger.warning("⚠️ File cleanup failed: %s", e)

        if (
            settings.ENABLE_AI_SUMMARIES
            or settings.ENABLE_AI_README
            or settings.ENABLE_AI_INSIGHTS
        ):
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2
                    ) as response:
                        if response.status == 200:
                            logger.info("✅ Ollama connected successfully")
                        else:
                            logger.warning("⚠️ Ollama returned status %s", response.status)
            except Exception as e:
                logger.warning("⚠️ Could not connect to Ollama at %s: %s",
                               settings.OLLAMA_BASE_URL, e)
                logger.warning("AI features will use fallback responses")

        logger.info("✅ Startup completed in %.2f seconds", time.time() - startup_time)
        app.state.startup_time = startup_time
        yield

    except Exception as e:
        logger.critical("❌ Startup failed: %s", e)
        raise
    finally:
        shutdown_start = time.time()
        logger.info("🛑 Shutting down CodeAtlas API")
        try:
            await task_queue.stop()
            logger.info("✅ Task queue stopped")
        except Exception as e:
            logger.error("❌ Error stopping task queue: %s", e)
        try:
            await close_db()
            logger.info("✅ Database connections closed")
        except Exception as e:
            logger.error("❌ Error closing database: %s", e)
        logger.info("🛑 Shutdown completed in %.2f seconds", time.time() - shutdown_start)


# -------------------------------------------------
# App
# -------------------------------------------------
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
    contact={"name": "CodeAtlas Support", "email": "support@codeatlas.ai"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    request_id = f"req_{int(time.time())}"
    request.state.request_id = request_id

    logger.info("📥 %s %s from %s", request.method, request.url.path,
                request.client.host if request.client else "unknown")
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        logger.info("📤 %s %s -> %s (%.1fms)", request.method,
                    request.url.path, response.status_code, process_time)
        return response
    except Exception as exc:
        process_time = (time.time() - start_time) * 1000
        logger.error("❌ %s %s -> Exception: %s (%.1fms)", request.method,
                     request.url.path, str(exc), process_time)
        raise


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error: %s", exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning("HTTP error: %s %s", exc.status_code, exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", str(exc), exc_info=True)
    detail = str(exc) if settings.DEBUG else "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail,
                                                  "error_code": "INTERNAL_ERROR"})


# -------------------------------------------------
# Root routes
# -------------------------------------------------
@app.get("/", include_in_schema=False)
async def root() -> Dict[str, Any]:
    return {
        "message": "Welcome to CodeAtlas API",
        "version": settings.API_VERSION,
        "status": "operational",
        "documentation": "/docs" if settings.DEBUG else None,
        "ai_features": {
            "enabled": {
                "summaries": settings.ENABLE_AI_SUMMARIES,
                "readme": settings.ENABLE_AI_README,
                "insights": settings.ENABLE_AI_INSIGHTS,
            },
            "model": settings.LLM_MODEL,
            "provider": settings.LLM_PROVIDER,
        },
    }


@app.get("/health", include_in_schema=False)
async def health_check():
    return {
        "status": "healthy",
        "service": "codeatlas-api",
        "timestamp": time.time(),
        "version": settings.API_VERSION,
    }


for mount_path, directory, name in [
    ("/static", "storage", "static"),
    ("/uploads", settings.UPLOAD_DIR, "uploads"),
    ("/reports", settings.REPORT_DIR, "reports"),
    ("/exports", settings.EXPORT_DIR, "exports"),
]:
    try:
        app.mount(mount_path, StaticFiles(directory=directory, html=(name == "static")), name=name)
    except Exception as e:
        logger.debug("Mount %s skipped: %s", mount_path, e)


# -------------------------------------------------
# Register routers
# -------------------------------------------------
if "health" in routers:
    app.include_router(routers["health"], tags=["health"])
if "analyze" in routers:
    app.include_router(routers["analyze"], tags=["analyze"], prefix="/api")
if "upload" in routers:
    app.include_router(routers["upload"], tags=["upload"], prefix="/api")
if "reports" in routers:
    app.include_router(routers["reports"], tags=["reports"], prefix="/api")
if "auth" in routers:
    app.include_router(routers["auth"], tags=["auth"], prefix="/api")
if "webhooks" in routers:
    app.include_router(routers["webhooks"], tags=["webhooks"], prefix="/api")
if "ai" in routers:
    app.include_router(routers["ai"], prefix="/api", tags=["ai"])
if "admin" in routers and settings.DEBUG:
    app.include_router(routers["admin"], tags=["admin"], prefix="/api/admin")


# -------------------------------------------------
# WebSockets
# -------------------------------------------------
@app.websocket("/ws/status/{task_id}")
async def websocket_status(websocket: WebSocket, task_id: str):
    await ws_manager.connect(websocket, task_id)
    try:
        while True:
            status = task_queue.get_status(task_id)
            if not status:
                await websocket.send_json({"error": "Task not found", "task_id": task_id})
                break
            await websocket.send_json({**status, "timestamp": time.time()})
            if status.get("status") in {"completed", "failed", "cancelled"}:
                break
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for task %s", task_id)
    except Exception as e:
        logger.error("WebSocket error for task %s: %s", task_id, e)
    finally:
        ws_manager.disconnect(task_id)


@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat", "timestamp": time.time()})
    except WebSocketDisconnect:
        logger.info("Notification WebSocket disconnected")
    except Exception as e:
        logger.error("Notification WebSocket error: %s", e)


# -------------------------------------------------
# Custom OpenAPI
# -------------------------------------------------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {})["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key for authentication",
        }
    }
    schema["security"] = [{"ApiKeyAuth": []}]
    schema["tags"] = [
        {"name": "health", "description": "Health checks"},
        {"name": "analyze", "description": "Code analysis"},
        {"name": "upload", "description": "File uploads"},
        {"name": "reports", "description": "Reports"},
        {"name": "auth", "description": "Authentication"},
        {"name": "webhooks", "description": "Webhooks"},
        {"name": "ai", "description": "AI-powered features"},
    ]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


# -------------------------------------------------
# Entry point (used by `codeatlas-api` script)
# -------------------------------------------------
def run() -> None:
    import uvicorn

    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║   🚀 CodeAtlas API - AI-Powered Code Intelligence        ║
    ║   Version: {settings.API_VERSION:<46}║
    ║   AI Model: {settings.LLM_MODEL:<45}║
    ║   Docs: http://localhost:{settings.PORT}/docs{' ' * (31 - len(str(settings.PORT)))}║
    ╚══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
        access_log=False,
    )


if __name__ == "__main__":
    run()