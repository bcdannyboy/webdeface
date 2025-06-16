"""Simple API token authentication endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...utils.logging import get_structured_logger
from ..auth import get_current_user

logger = get_structured_logger(__name__)

router = APIRouter()


class TokenInfoResponse(BaseModel):
    """Token info response model."""

    valid: bool
    user_id: str
    role: str
    permissions: list[str]


@router.get("/token/verify", response_model=TokenInfoResponse)
async def verify_token(
    current_user: dict[str, Any] = Depends(get_current_user)
) -> TokenInfoResponse:
    """Verify API token and return user information."""

    return TokenInfoResponse(
        valid=True,
        user_id=current_user["id"],
        role=current_user["role"],
        permissions=current_user["permissions"],
    )


@router.get("/token/info", response_model=dict[str, str])
async def token_info() -> dict[str, str]:
    """Get information about API token authentication."""

    return {
        "message": "API uses Bearer token authentication",
        "header": "Authorization: Bearer <your-api-token>",
        "note": "Contact administrator for API token",
    }
