"""
Health endpoints.

/health is public and intentionally minimal: status, version, uptime.
Host CPU / memory / disk numbers describe Render's shared machine (not
your service) and tell an attacker about the infrastructure, so they are
only exposed by /health/detailed when DEBUG is on.
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.core.config import settings

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

router = APIRouter(prefix="/health", tags=["health"])

# Measured from when THIS process started. The old code used
# psutil.boot_time(), i.e. the host's uptime, which showed thousands of
# hours on a service that had just been deployed.
_PROCESS_START = time.time()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uptime() -> str:
    seconds = int(time.time() - _PROCESS_START)
    return f"{seconds // 3600}h {(seconds % 3600) // 60}m {seconds % 60}s"


@router.get("", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "CodeAtlas",
        "timestamp": _now(),
        "version": settings.API_VERSION,
        "uptime": _uptime(),
    }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not Found")

    response: Dict[str, Any] = {
        "status": "healthy",
        "service": "CodeAtlas",
        "timestamp": _now(),
        "version": settings.API_VERSION,
        "uptime": _uptime(),
    }
    if not PSUTIL_AVAILABLE:
        response["system"] = {"message": "psutil not installed"}
        return response

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    process = psutil.Process()
    response["system"] = {
        "cpu": {"percent": psutil.cpu_percent(interval=0.1), "cores": psutil.cpu_count()},
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_percent": memory.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            # was labelled free_percent but held the USED percentage
            "used_percent": disk.percent,
        },
        "process": {
            "pid": process.pid,
            "memory_mb": round(process.memory_info().rss / (1024**2), 1),
            "num_threads": process.num_threads(),
        },
    }
    return response


@router.get("/ready")
async def readiness_probe() -> Dict[str, Any]:
    return {"status": "ready", "service": "CodeAtlas", "timestamp": _now()}


@router.get("/live")
async def liveness_probe() -> Dict[str, Any]:
    return {"status": "alive", "service": "CodeAtlas", "timestamp": _now()}