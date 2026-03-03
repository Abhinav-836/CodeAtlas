"""
API key dependency for authentication.
"""
from typing import Optional

from fastapi import Header, HTTPException
from app.core.config import settings


async def get_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """
    Validate API key.
    
    Args:
        x_api_key: API key from header
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Use header: X-API-Key"
        )
    
    # Check against configured API key
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return x_api_key


async def optional_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> Optional[str]:
    """
    Optional API key validation.
    
    Args:
        x_api_key: Optional API key
        
    Returns:
        API key if provided and valid, None otherwise
    """
    if not x_api_key:
        return None
    
    try:
        return await get_api_key(x_api_key)
    except HTTPException:
        return None