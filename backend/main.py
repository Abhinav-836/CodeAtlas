"""
FastAPI application entry point - CodeAtlas API
"""

import asyncio
import logging
import time
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

# -------------------------------------------------
# Settings (inlined to avoid import errors)
# -------------------------------------------------
class Settings:
    """Simple settings class."""
    # API
    API_TITLE = os.getenv("API_TITLE", "CodeAtlas API")
    API_VERSION = os.getenv("API_VERSION", "1.0.0")
    API_DESCRIPTION = os.getenv("API_DESCRIPTION", "AI-powered code intelligence platform")
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    
    # Security
    API_KEY = os.getenv("API_KEY", "dev-key-change-in-production")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Database - CRITICAL FIX: Use aiosqlite for async SQLite
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./codeatlas.db")
    
    # File storage
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "storage/uploads")
    REPORT_DIR = os.getenv("REPORT_DIR", "storage/reports")
    EXPORT_DIR = os.getenv("EXPORT_DIR", "storage/exports")
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "104857600"))  # 100MB
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    
    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    # Features
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "false").lower() == "true"
    ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "false").lower() == "true"
    CLEANUP_ON_STARTUP = os.getenv("CLEANUP_ON_STARTUP", "true").lower() == "true"
    
    # AI Features
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-oss:20b-cloud")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
    ENABLE_AI_SUMMARIES = os.getenv("ENABLE_AI_SUMMARIES", "true").lower() == "true"
    ENABLE_AI_README = os.getenv("ENABLE_AI_README", "true").lower() == "true"
    ENABLE_AI_INSIGHTS = os.getenv("ENABLE_AI_INSIGHTS", "true").lower() == "true"

settings = Settings()

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# File utilities (inlined)
# -------------------------------------------------
def ensure_dir(directory):
    """Ensure a directory exists."""
    os.makedirs(directory, exist_ok=True)
    return directory

def cleanup_old_files(directory, max_age_hours=24):
    """Clean up files older than specified hours."""
    import time
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
    """Simple WebSocket connection manager."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """Connect WebSocket for a specific task."""
        await websocket.accept()
        self.active_connections[task_id] = websocket
        logger.info("WebSocket connected for task %s", task_id)
    
    def disconnect(self, task_id: str):
        """Disconnect WebSocket for a task."""
        if task_id in self.active_connections:
            del self.active_connections[task_id]
            logger.info("WebSocket disconnected for task %s", task_id)

ws_manager = ConnectionManager()

# -------------------------------------------------
# Try to import optional modules with fallbacks
# -------------------------------------------------

# Try to import database functions
try:
    from app.db.session import init_db, close_db, check_db_health
    logger.info("✅ Using database functions from app.db.session")
except ImportError:
    logger.warning("⚠️ Database module not found, using stubs")
    
    async def init_db():
        """Initialize database (stub)."""
        logger.info("Database initialization skipped")
    
    async def close_db():
        """Close database connections (stub)."""
        pass
    
    async def check_db_health():
        """Check database health (stub)."""
        return {"status": "unknown", "message": "Database module not loaded"}

# Try to import task queue
try:
    from app.workers.task_queue import task_queue
    logger.info("✅ Using real task queue")
except ImportError:
    logger.warning("⚠️ Real task queue not found, creating simple task queue")
    
    class SimpleTaskQueue:
        """Simple in-memory task queue for fallback."""
        
        def __init__(self):
            self.tasks = {}
            self.results = {}
            self._running = False
        
        async def start(self):
            self._running = True
            logger.info("Simple task queue started")
        
        async def stop(self):
            self._running = False
            logger.info("Simple task queue stopped")
        
        async def enqueue(self, func, *args, **kwargs):
            import uuid
            task_id = f"task_{uuid.uuid4().hex[:10]}"
            
            self.tasks[task_id] = {
                "task_id": task_id,
                "function": func.__name__ if hasattr(func, '__name__') else str(func),
                "status": "queued",
                "created_at": time.time()
            }
            
            # Run task in background
            asyncio.create_task(self._execute_task(task_id, func, *args, **kwargs))
            return task_id
        
        async def _execute_task(self, task_id, func, *args, **kwargs):
            try:
                self.tasks[task_id]["status"] = "running"
                self.tasks[task_id]["started_at"] = time.time()
                
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                
                self.tasks[task_id]["status"] = "completed"
                self.tasks[task_id]["completed_at"] = time.time()
                self.results[task_id] = result
                
            except Exception as e:
                self.tasks[task_id]["status"] = "failed"
                self.tasks[task_id]["error"] = str(e)
                self.tasks[task_id]["completed_at"] = time.time()
                logger.error("Task %s failed: %s", task_id, e)
        
        def get_status(self, task_id):
            return self.tasks.get(task_id)
        
        async def get_result(self, task_id, timeout=30):
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
    
    task_queue = SimpleTaskQueue()

# -------------------------------------------------
# Import routers dynamically
# -------------------------------------------------
def import_router(router_name):
    """Import a single router dynamically."""
    try:
        if router_name == "analyze":
            from app.api.routes.analyze import router
            print(f"✅ Successfully imported analyze router")
            return router
        elif router_name == "upload":
            from app.api.routes.upload import router
            return router
        elif router_name == "reports":
            from app.api.routes.reports import router
            return router
        elif router_name == "health":
            from app.api.routes.health import router
            return router
        elif router_name == "ai":
            from app.api.routes.ai import router
            return router
        else:
            return None
    except ImportError as e:
        logger.warning(f"⚠️ Could not import router '{router_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error importing router '{router_name}': {e}")
        return None
        
        logger.info(f"✅ Imported router: {router_name}")
        return router
    except ImportError as e:
        if router_name != "admin" or settings.DEBUG:
            logger.warning(f"⚠️ Could not import router '{router_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error importing router '{router_name}': {e}")
        return None

# Import all available routers
routers = {}
router_names = ["health", "analyze", "upload", "reports", "auth", "webhooks", "ai"]
if settings.DEBUG:
    router_names.append("admin")

for name in router_names:
    router = import_router(name)
    if router:
        routers[name] = router

# -------------------------------------------------
# Lifespan
# -------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    startup_time = time.time()
    logger.info("🚀 Starting CodeAtlas API v%s", settings.API_VERSION)
    
    try:
        # Ensure directories exist
        required_dirs = [
            settings.UPLOAD_DIR,
            settings.REPORT_DIR,
            settings.EXPORT_DIR,
            "storage",
            "storage/tmp",
            "storage/logs",
            "storage/backups",
            "storage/task_results",
            "storage/repos"
        ]
        
        for directory in required_dirs:
            try:
                ensure_dir(directory)
                logger.debug("✅ Directory ensured: %s", directory)
            except Exception as e:
                logger.error("❌ Failed to create directory %s: %s", directory, e)
                if not settings.DEBUG:
                    raise
        
        # Initialize database
        try:
            await init_db()
            logger.info("✅ Database initialized")
        except Exception as e:
            logger.error("❌ Database initialization failed: %s", e)
        
        # Start task queue
        try:
            await task_queue.start()
            logger.info("✅ Task queue started")
        except Exception as e:
            logger.error("❌ Task queue failed to start: %s", e)
        
        # Cleanup old files on startup if enabled
        if settings.CLEANUP_ON_STARTUP:
            try:
                cleanup_old_files(settings.UPLOAD_DIR, max_age_hours=24)
                cleanup_old_files("storage/tmp", max_age_hours=1)
                cleanup_old_files("storage/task_results", max_age_hours=168)  # 7 days
                logger.info("✅ Old files cleaned up")
            except Exception as e:
                logger.warning("⚠️ File cleanup failed: %s", e)
        
        # Check Ollama connection if AI features are enabled
        if settings.ENABLE_AI_SUMMARIES or settings.ENABLE_AI_README or settings.ENABLE_AI_INSIGHTS:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2) as response:
                        if response.status == 200:
                            logger.info("✅ Ollama connected successfully")
                        else:
                            logger.warning("⚠️ Ollama returned status %s", response.status)
            except Exception as e:
                logger.warning("⚠️ Could not connect to Ollama at %s: %s", settings.OLLAMA_BASE_URL, e)
                logger.warning("AI features will use fallback responses")
        
        startup_duration = time.time() - startup_time
        logger.info("✅ Startup completed in %.2f seconds", startup_duration)
        
        # Store startup time
        app.state.startup_time = startup_time
        
        yield  # Application runs here
        
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
        
        shutdown_duration = time.time() - shutdown_start
        logger.info("🛑 Shutdown completed in %.2f seconds", shutdown_duration)


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
    servers=[
        {"url": "/", "description": "Current server"},
        {"url": "http://localhost:8000", "description": "Local development"}
    ] if settings.DEBUG else None,
    contact={
        "name": "CodeAtlas Support",
        "email": "support@codeatlas.ai"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# -------------------------------------------------
# Middleware
# -------------------------------------------------
# CORS Middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

# GZip Middleware
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,
)

# -------------------------------------------------
# Request logging middleware
# -------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = time.time()
    
    request_id = f"req_{int(time.time())}"
    request.state.request_id = request_id
    
    logger.info(
        "📥 %s %s from %s",
        request.method,
        request.url.path,
        request.client.host if request.client else "unknown"
    )
    
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        
        logger.info(
            "📤 %s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            process_time
        )
        
        return response
        
    except Exception as exc:
        process_time = (time.time() - start_time) * 1000
        logger.error(
            "❌ %s %s -> Exception: %s (%.1fms)",
            request.method,
            request.url.path,
            str(exc),
            process_time
        )
        raise

# -------------------------------------------------
# Exception Handlers
# -------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning("Validation error: %s", exc.errors())
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.warning("HTTP error: %s %s", exc.status_code, exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    logger.error("Unhandled exception: %s", str(exc), exc_info=True)
    
    detail = str(exc) if settings.DEBUG else "Internal server error"
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": detail,
            "error_code": "INTERNAL_ERROR"
        }
    )

# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.get("/", include_in_schema=False)
async def root() -> Dict[str, Any]:
    """Root endpoint with API information"""
    return {
        "message": "Welcome to CodeAtlas API",
        "version": settings.API_VERSION,
        "status": "operational",
        "documentation": "/docs" if settings.DEBUG else None,
        "ai_features": {
            "enabled": {
                "summaries": settings.ENABLE_AI_SUMMARIES,
                "readme": settings.ENABLE_AI_README,
                "insights": settings.ENABLE_AI_INSIGHTS
            },
            "model": settings.LLM_MODEL,
            "provider": settings.LLM_PROVIDER
        }
    }

@app.get("/health", include_in_schema=False)
async def health_check():
    """Quick health check"""
    return {
        "status": "healthy",
        "service": "codeatlas-api",
        "timestamp": time.time(),
        "version": settings.API_VERSION
    }

# Serve static files
try:
    app.mount("/static", StaticFiles(directory="storage", html=True), name="static")
except:
    pass

try:
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
except:
    pass

try:
    app.mount("/reports", StaticFiles(directory=settings.REPORT_DIR), name="reports")
except:
    pass

try:
    app.mount("/exports", StaticFiles(directory=settings.EXPORT_DIR), name="exports")
except:
    pass

# Include available routers
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
# WebSocket Endpoints
# -------------------------------------------------
@app.websocket("/ws/status/{task_id}")
async def websocket_status(websocket: WebSocket, task_id: str):
    """WebSocket for real-time task status updates"""
    await ws_manager.connect(websocket, task_id)
    
    try:
        while True:
            status = task_queue.get_status(task_id)
            
            if not status:
                await websocket.send_json({
                    "error": "Task not found",
                    "task_id": task_id,
                })
                break
            
            await websocket.send_json({
                **status,
                "timestamp": time.time()
            })
            
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
    """WebSocket for general notifications"""
    await websocket.accept()
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": time.time()
                    })
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": time.time()
                })
            
    except WebSocketDisconnect:
        logger.info("Notification WebSocket disconnected")
    except Exception as e:
        logger.error("Notification WebSocket error: %s", e)

# -------------------------------------------------
# OpenAPI Schema
# -------------------------------------------------
def custom_openapi():
    """Customize OpenAPI schema"""
    if app.openapi_schema:
        return app.openapi_schema
    
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key for authentication"
        }
    }
    
    schema["security"] = [{"ApiKeyAuth": []}]
    
    # Add tags
    schema["tags"] = []
    if "health" in routers:
        schema["tags"].append({"name": "health", "description": "Health checks"})
    if "analyze" in routers:
        schema["tags"].append({"name": "analyze", "description": "Code analysis"})
    if "upload" in routers:
        schema["tags"].append({"name": "upload", "description": "File uploads"})
    if "reports" in routers:
        schema["tags"].append({"name": "reports", "description": "Reports"})
    if "auth" in routers:
        schema["tags"].append({"name": "auth", "description": "Authentication"})
    if "webhooks" in routers:
        schema["tags"].append({"name": "webhooks", "description": "Webhooks"})
    if "ai" in routers:
        schema["tags"].append({"name": "ai", "description": "AI-powered features"})
    if "admin" in routers and settings.DEBUG:
        schema["tags"].append({"name": "admin", "description": "Administrative"})
    
    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi

# -------------------------------------------------
# Main Entry Point
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║   🚀 CodeAtlas API - AI-Powered Code Intelligence        ║
    ║                                                          ║
    ║   Version: 1.0.0                                         ║
    ║   AI Model: {}                                           ║
    ║   Docs: http://localhost:8000/docs                       ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """.format(settings.LLM_MODEL))
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
        access_log=False,
    )