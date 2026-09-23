"""
API key dependency for authentication.

NOTE: Currently NOT applied to any route - the API is intentionally open.
To re-enable, add `dependencies=[Depends(get_api_key)]` to the route
decorators that should be protected.
"""
import hmac
from typing import Optional

from fastapi import Header, HTTPException

from app.core.config import settings


async def get_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Use header: X-API-Key",
        )
    if not hmac.compare_digest(str(x_api_key), str(settings.API_KEY)):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


async def optional_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[str]:
    if not x_api_key:
        return None
    try:
        return await get_api_key(x_api_key)
    except HTTPException:
        return None