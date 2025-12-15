"""SSO Service for ERPNext integration"""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.exceptions import not_found_exception, forbidden_exception
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.sso import SSOTokenResponse

import logging

log = logging.getLogger(__name__)


class SSOService:
    """Service for SSO token generation and validation"""

    SSO_TOKEN_TTL = 60  # seconds
    SSO_TOKEN_PREFIX = "sso:token:"

    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.settings = get_settings()

    async def generate_erpnext_token(
        self, user_id: UUID, tenant_id: UUID
    ) -> SSOTokenResponse:
        """
        Generate one-time SSO token for ERPNext login

        Args:
            user_id: User UUID
            tenant_id: Tenant UUID

        Returns:
            SSOTokenResponse with token and URL

        Raises:
            HTTPException: If tenant not found or not active
        """
        # Fetch tenant
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise not_found_exception("Tenant not found")

        if not tenant.erpnext_site_url:
            raise forbidden_exception("ERPNext site not provisioned yet")

        # Generate secure random token
        token = secrets.token_urlsafe(32)

        # Store token in Redis with TTL
        token_key = f"{self.SSO_TOKEN_PREFIX}{token}"
        token_data = {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "created_at": datetime.utcnow().isoformat(),
        }

        await self.redis.hset(token_key, mapping=token_data)
        await self.redis.expire(token_key, self.SSO_TOKEN_TTL)

        # Build SSO URL
        base_url = tenant.erpnext_site_url.rstrip("/")
        sso_url = f"{base_url}/api/method/erpmax.sso.login?token={token}"

        expires_at = datetime.utcnow() + timedelta(seconds=self.SSO_TOKEN_TTL)

        log.info(f"Generated SSO token for user {user_id} to tenant {tenant_id}")

        return SSOTokenResponse(sso_url=sso_url, token=token, expires_at=expires_at)

    async def validate_token(self, token: str) -> tuple[UUID, UUID]:
        """
        Validate SSO token and return user_id, tenant_id

        Args:
            token: SSO token string

        Returns:
            Tuple of (user_id, tenant_id)

        Raises:
            HTTPException: If token invalid or expired
        """
        token_key = f"{self.SSO_TOKEN_PREFIX}{token}"

        # Fetch token data from Redis
        token_data = await self.redis.hgetall(token_key)

        if not token_data:
            raise forbidden_exception("Invalid or expired SSO token")

        # Delete token (one-time use)
        await self.redis.delete(token_key)

        user_id = UUID(token_data[b"user_id"].decode())
        tenant_id = UUID(token_data[b"tenant_id"].decode())

        log.info(f"Validated SSO token for user {user_id} to tenant {tenant_id}")

        return user_id, tenant_id

    async def get_user_session_data(self, user_id: UUID, tenant_id: UUID) -> dict:
        """
        Get user and tenant data for ERPNext session

        Args:
            user_id: User UUID
            tenant_id: Tenant UUID

        Returns:
            Dict with user and tenant info
        """
        # Fetch user
        user_stmt = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        # Fetch tenant
        tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
        tenant_result = await self.db.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()

        if not user or not tenant:
            raise not_found_exception("User or tenant not found")

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
            },
            "tenant": {"id": str(tenant.id), "name": tenant.name, "slug": tenant.slug},
        }
