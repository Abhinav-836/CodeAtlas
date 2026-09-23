"""
API key dependency for authentication.
"""
import hmac
from typing import Optional

from fastapi import Header, HTTPException

from app.core.config import settings


async def get_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """
    Validate API key.

    Raises 401 if header is missing or does not match settings.API_KEY.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Use header: X-API-Key",
        )

    # Constant-time comparison to avoid timing leaks.
    if not hmac.compare_digest(str(x_api_key), str(settings.API_KEY)):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return x_api_key


async def optional_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[str]:
    """
    Optional API key validation.

    Returns the key on success, or None if missing/invalid. Never raises.
    """
    if not x_api_key:
        return None
    try:
        return await get_api_key(x_api_key)
    except HTTPException:
        return None