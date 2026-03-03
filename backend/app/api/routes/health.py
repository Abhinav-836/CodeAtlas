import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
import psutil  # Optional: for system metrics

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Health status with basic system information
    """
    try:
        # Basic health response
        response = {
            "status": "healthy",
            "service": "CodeAtlas",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.0",  # Consider getting from config/pyproject.toml
            "uptime": _get_uptime(),
        }
        
        # Add system info if psutil is available
        try:
            response.update(_get_system_info())
        except ImportError:
            # psutil not installed, skip system info
            pass
            
        return response
        
    except Exception as e:
        # Even if something fails, return an error status
        return {
            "status": "unhealthy",
            "service": "CodeAtlas",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
        }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with system metrics.
    
    Returns:
        Comprehensive health and system information
    """
    try:
        response = {
            "status": "healthy",
            "service": "CodeAtlas",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.0",
            "uptime": _get_uptime(),
        }
        
        # Add detailed system metrics if psutil is available
        try:
            import psutil
            system_info = _get_system_info()
            
            # Add process-specific info
            process = psutil.Process()
            system_info.update({
                "process": {
                    "pid": process.pid,
                    "name": process.name(),
                    "status": process.status(),
                    "cpu_percent": process.cpu_percent(interval=0.1),
                    "memory_percent": process.memory_percent(),
                    "num_threads": process.num_threads(),
                }
            })
            
            response["system"] = system_info
            
        except ImportError:
            response["system"] = {"message": "psutil not installed for detailed metrics"}
            
        return response
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "CodeAtlas",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
        }


@router.get("/ready")
async def readiness_probe() -> Dict[str, Any]:
    """
    Readiness probe for Kubernetes/container orchestration.
    
    Checks if the service is ready to accept traffic.
    """
    try:
        # Add checks for critical dependencies
        checks = {
            "api": True,
            # Add more checks as needed:
            # "database": check_database_connection(),
            # "cache": check_cache_connection(),
            # "storage": check_storage_access(),
        }
        
        all_ready = all(checks.values())
        
        return {
            "status": "ready" if all_ready else "not_ready",
            "service": "CodeAtlas",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": checks,
        }
        
    except Exception as e:
        return {
            "status": "not_ready",
            "service": "CodeAtlas",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
        }


@router.get("/live")
async def liveness_probe() -> Dict[str, Any]:
    """
    Liveness probe for Kubernetes/container orchestration.
    
    Checks if the service is still alive.
    """
    return {
        "status": "alive",
        "service": "CodeAtlas",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# Helper functions
def _get_uptime() -> str:
    """Get formatted uptime string."""
    uptime_seconds = time.time() - psutil.boot_time() if 'psutil' in globals() else 0
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    return f"{hours}h {minutes}m {seconds}s"


def _get_system_info() -> Dict[str, Any]:
    """Get system information using psutil."""
    import psutil
    
    # CPU information
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count()
    
    # Memory information
    memory = psutil.virtual_memory()
    
    # Disk information
    disk = psutil.disk_usage('/')
    
    return {
        "cpu": {
            "percent": cpu_percent,
            "cores": cpu_count,
            "cores_logical": psutil.cpu_count(logical=True),
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_percent": memory.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_percent": disk.percent,
        },
    }


# Optional: Add dependency health checks
def get_app_version() -> str:
    """Get application version from config."""
    # You could read this from pyproject.toml, setup.py, or environment variable
    import importlib.metadata
    try:
        return importlib.metadata.version("codeatlas")
    except:
        return "1.0.0"