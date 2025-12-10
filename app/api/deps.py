from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import verify_token
from app.core.exceptions import (
    credentials_exception,
    forbidden_exception,
    inactive_user_exception,
    invalid_tenant_exception,
)
from app.models import User, Tenant, UserTenant
from app.models.enums import TenantRole


# Security scheme
security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer token
        db: Database session

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    try:
        payload = verify_token(token, token_type="access")
        user_id: str = payload.get("sub")

        if user_id is None:
            raise credentials_exception()

    except JWTError:
        raise credentials_exception()

    # Get user from database
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception("User not found")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (must be active)

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise inactive_user_exception()

    return current_user


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Tenant:
    """
    Get current tenant from JWT token

    Args:
        credentials: HTTP Bearer token
        db: Database session
        current_user: Current authenticated user

    Returns:
        Tenant: Current tenant

    Raises:
        HTTPException: If tenant not found or user doesn't have access
    """
    token = credentials.credentials

    try:
        payload = verify_token(token, token_type="access")
        tenant_id_str: Optional[str] = payload.get("tenant_id")

        if tenant_id_str is None:
            raise credentials_exception("No tenant in token")

        tenant_id = UUID(tenant_id_str)

    except (JWTError, ValueError):
        raise credentials_exception()

    # Check if user has access to this tenant
    result = await db.execute(
        select(UserTenant)
        .where(UserTenant.user_id == current_user.id)
        .where(UserTenant.tenant_id == tenant_id)
    )
    user_tenant = result.scalar_one_or_none()

    if user_tenant is None:
        raise invalid_tenant_exception()

    # Get tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise credentials_exception("Tenant not found")

    return tenant


async def get_current_user_tenant(
    current_user: User = Depends(get_current_active_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> UserTenant:
    """
    Get current user's tenant relationship

    Args:
        current_user: Current authenticated user
        current_tenant: Current tenant
        db: Database session

    Returns:
        UserTenant: User-tenant relationship with role
    """
    result = await db.execute(
        select(UserTenant)
        .where(UserTenant.user_id == current_user.id)
        .where(UserTenant.tenant_id == current_tenant.id)
    )
    user_tenant = result.scalar_one_or_none()

    if user_tenant is None:
        raise invalid_tenant_exception()

    return user_tenant


def require_role(*allowed_roles: TenantRole):
    """
    Dependency factory for role-based access control

    Args:
        *allowed_roles: Roles that are allowed to access the endpoint

    Returns:
        Dependency function that checks user role

    Example:
        @router.get("/admin-only", dependencies=[Depends(require_role(TenantRole.OWNER, TenantRole.ADMIN))])
    """

    async def role_checker(
        user_tenant: UserTenant = Depends(get_current_user_tenant),
    ) -> UserTenant:
        if user_tenant.role not in allowed_roles:
            raise forbidden_exception(
                f"This action requires one of the following roles: {', '.join(r.value for r in allowed_roles)}"
            )
        return user_tenant

    return role_checker


def require_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Dependency for requiring superuser access

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current user if superuser

    Raises:
        HTTPException: If user is not superuser
    """
    if not current_user.is_superuser:
        raise forbidden_exception("Superuser access required")

    return current_user


class Pagination:
    """Pagination parameters"""

    def __init__(
        self,
        page: int = 1,
        size: int = 20,
    ):
        self.page = max(1, page)
        self.size = min(100, max(1, size))
        self.skip = (self.page - 1) * self.size
        self.limit = self.size

    def get_pagination_info(self, total: int) -> dict:
        """Get pagination metadata"""
        pages = (total + self.size - 1) // self.size

        return {
            "total": total,
            "page": self.page,
            "size": self.size,
            "pages": pages,
        }
