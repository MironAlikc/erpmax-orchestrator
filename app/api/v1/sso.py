"""SSO API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.api.deps import get_current_user, get_current_tenant
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.base import SingleResponse
from app.schemas.sso import SSOTokenResponse
from app.services.sso import SSOService

router = APIRouter()


@router.post("/erpnext/token", response_model=SingleResponse[SSOTokenResponse])
async def create_erpnext_sso_token(
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """
    Generate one-time SSO token for ERPNext login

    - **Returns**: SSO URL with token and expiration time
    - **Token validity**: 60 seconds
    - **One-time use**: Token is deleted after validation

    The generated URL can be used to automatically log in to ERPNext
    without requiring credentials.
    """
    sso_service = SSOService(db, redis_client)

    token_response = await sso_service.generate_erpnext_token(
        user_id=current_user.id, tenant_id=current_tenant.id
    )

    return SingleResponse(status="success", data=token_response)


@router.get("/erpnext/callback")
async def erpnext_sso_callback(
    token: str = Query(..., description="One-time SSO token"),
    redirect: str = Query("/desk", description="Redirect path after login"),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """
    Validate SSO token and return user session data

    This endpoint is called by ERPNext to validate the SSO token
    and retrieve user information for session creation.

    - **token**: One-time SSO token (required)
    - **redirect**: Path to redirect after login (default: /desk)

    Returns user and tenant data for ERPNext session creation.
    """
    sso_service = SSOService(db, redis_client)

    try:
        # Validate token and get user/tenant IDs
        user_id, tenant_id = await sso_service.validate_token(token)

        # Get user session data
        session_data = await sso_service.get_user_session_data(user_id, tenant_id)

        # Return session data (ERPNext will use this to create session)
        return {"success": True, "data": session_data, "redirect": redirect}

    except HTTPException as e:
        # Return error response
        return {"success": False, "error": e.detail, "redirect": "/login"}


@router.get("/erpnext/validate/{token}")
async def validate_sso_token(
    token: str,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """
    Validate SSO token without consuming it

    This is a helper endpoint for checking token validity
    without deleting it from Redis.

    **Note**: This endpoint does NOT consume the token.
    Use /erpnext/callback for actual SSO flow.
    """
    token_key = f"{SSOService.SSO_TOKEN_PREFIX}{token}"

    token_data = await redis_client.hgetall(token_key)

    if not token_data:
        raise HTTPException(status_code=404, detail="Token not found or expired")

    return {
        "valid": True,
        "user_id": token_data[b"user_id"].decode(),
        "tenant_id": token_data[b"tenant_id"].decode(),
        "created_at": token_data[b"created_at"].decode(),
    }
