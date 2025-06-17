"""Simple API token authentication."""

from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import get_settings
from ..utils.logging import get_structured_logger
from .types import APIError

logger = get_structured_logger(__name__)

# API token security
security = HTTPBearer()


class AuthError(APIError):
    """Authentication related errors."""

    pass


def setup_auth(app, settings) -> None:
    """Setup authentication for the FastAPI application."""
    # Store auth settings in app state
    app.state.api_tokens = getattr(settings, "api_tokens", ["dev-token-12345"])


def verify_api_token(token: str) -> bool:
    """Verify API token."""
    # Handle None token case
    if token is None:
        logger.debug("Token verification result", token_valid=False)
        return False
        
    settings = get_settings()
    valid_tokens = getattr(settings, "api_tokens", ["dev-token-12345"])

    # DEBUG: Log authentication attempt details
    logger.debug(
        "Token verification attempt",
        token=token[:8] + "..." if len(token) > 8 else token,
        valid_tokens=[t[:8] + "..." if len(t) > 8 else t for t in valid_tokens],
        settings_type=type(settings).__name__,
        has_api_tokens=hasattr(settings, "api_tokens"),
    )

    result = token in valid_tokens
    logger.debug("Token verification result", token_valid=result)
    return result


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """Get current authenticated user from API token."""

    try:
        if not verify_api_token(credentials.credentials):
            raise AuthError("Invalid API token")

        # Return a simple user object for API token auth
        user = {
            "id": "api-user",
            "username": "api",
            "role": "api",
            "permissions": ["read", "write"],
            "token": credentials.credentials,
        }

        return user

    except AuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """Get current active user."""
    if not current_user.get("active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


def require_permission(permission: str):
    """Decorator to require specific permission."""

    def permission_checker(
        current_user: dict[str, Any] = Depends(get_current_active_user)
    ) -> dict[str, Any]:
        user_permissions = current_user.get("permissions", [])
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires '{permission}'",
            )
        return current_user

    return permission_checker


# Optional dependency - can be used to make auth optional on some endpoints
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[dict[str, Any]]:
    """Get current user if token is provided, otherwise return None."""
    if credentials is None:
        return None

    try:
        if verify_api_token(credentials.credentials):
            return {
                "id": "api-user",
                "username": "api",
                "role": "api",
                "permissions": ["read", "write"],
                "token": credentials.credentials,
            }
    except Exception:
        pass

    return None


def require_permission(permission: str):
    """Decorator to require specific permission."""

    def permission_checker(
        current_user: dict[str, Any] = Depends(get_current_user)
    ) -> dict[str, Any]:
        user_permissions = current_user.get("permissions", [])
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires '{permission}'",
            )
        return current_user

    return permission_checker
