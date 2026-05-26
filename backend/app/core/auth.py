from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    """
    FastAPI dependency that enforces X-API-Key header authentication.
    If API_KEY is empty in settings, auth is disabled (open access for dev).
    """
    settings = get_settings()
    if not settings.api_key:
        return "anonymous"
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key. Provide X-API-Key header.",
        )
    return api_key
