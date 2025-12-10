"""Tenant service - business logic for tenant management"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    NotFoundError,
    AuthorizationError,
    AlreadyExistsError,
    ValidationError,
)
from app.models import Tenant, User, UserTenant, Subscription
from app.models.enums import TenantRole, TenantStatus
from app.schemas.tenant import TenantCreate, TenantUpdate


class TenantService:
    """Tenant management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_tenants(
        self,
        user_id: UUID,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Tenant], int]:
        """
        Get all tenants for a user

        Args:
            user_id: User ID
            page: Page number
            size: Items per page

        Returns:
            Tuple of (tenants, total_count)
        """
        # Count total
        count_query = (
            select(func.count(Tenant.id))
            .join(UserTenant, UserTenant.tenant_id == Tenant.id)
            .where(UserTenant.user_id == user_id)
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Get tenants
        offset = (page - 1) * size
        query = (
            select(Tenant)
            .join(UserTenant, UserTenant.tenant_id == Tenant.id)
            .where(UserTenant.user_id == user_id)
            .offset(offset)
            .limit(size)
            .order_by(Tenant.created_at.desc())
        )

        result = await self.db.execute(query)
        tenants = result.scalars().all()

        return list(tenants), total

    async def get_current_tenant(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Tenant:
        """
        Get current tenant with subscription

        Args:
            tenant_id: Tenant ID
            user_id: User ID (for access check)

        Returns:
            Tenant with subscription

        Raises:
            NotFoundError: If tenant not found
            AuthorizationError: If user doesn't have access
        """
        # Check access
        await self._check_user_access(user_id, tenant_id)

        # Get tenant with subscription
        query = (
            select(Tenant)
            .where(Tenant.id == tenant_id)
            .options(selectinload(Tenant.subscriptions))
        )

        result = await self.db.execute(query)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise NotFoundError("Tenant")

        return tenant

    async def get_tenant_by_id(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Tenant:
        """
        Get tenant by ID

        Args:
            tenant_id: Tenant ID
            user_id: User ID (for access check)

        Returns:
            Tenant

        Raises:
            NotFoundError: If tenant not found
            AuthorizationError: If user doesn't have access
        """
        # Check access
        await self._check_user_access(user_id, tenant_id)

        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise NotFoundError("Tenant")

        return tenant

    async def update_tenant(
        self,
        tenant_id: UUID,
        user_id: UUID,
        data: TenantUpdate,
    ) -> Tenant:
        """
        Update tenant

        Args:
            tenant_id: Tenant ID
            user_id: User ID (for permission check)
            data: Update data

        Returns:
            Updated tenant

        Raises:
            NotFoundError: If tenant not found
            AuthorizationError: If user doesn't have permission
        """
        # Check permission (owner or admin only)
        await self._check_user_permission(
            user_id,
            tenant_id,
            [TenantRole.OWNER, TenantRole.ADMIN],
        )

        # Get tenant
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise NotFoundError("Tenant")

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)

        await self.db.commit()
        await self.db.refresh(tenant)

        return tenant

    async def get_tenant_users(
        self,
        tenant_id: UUID,
        user_id: UUID,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict], int]:
        """
        Get all users in a tenant

        Args:
            tenant_id: Tenant ID
            user_id: Current user ID (for permission check)
            page: Page number
            size: Items per page

        Returns:
            Tuple of (users_data, total_count)

        Raises:
            AuthorizationError: If user doesn't have permission
        """
        # Check permission (owner or admin only)
        await self._check_user_permission(
            user_id,
            tenant_id,
            [TenantRole.OWNER, TenantRole.ADMIN],
        )

        # Count total
        count_query = select(func.count(UserTenant.user_id)).where(
            UserTenant.tenant_id == tenant_id
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Get users
        offset = (page - 1) * size
        query = (
            select(UserTenant, User)
            .join(User, UserTenant.user_id == User.id)
            .where(UserTenant.tenant_id == tenant_id)
            .offset(offset)
            .limit(size)
            .order_by(UserTenant.joined_at.desc())
        )

        result = await self.db.execute(query)

        users_data = []
        for user_tenant, user in result.all():
            users_data.append(
                {
                    "user_id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user_tenant.role.value,
                    "is_default": user_tenant.is_default,
                    "joined_at": user_tenant.joined_at.isoformat(),
                }
            )

        return users_data, total

    async def invite_user(
        self,
        tenant_id: UUID,
        current_user_id: UUID,
        email: str,
        role: TenantRole,
    ) -> dict:
        """
        Invite user to tenant

        Args:
            tenant_id: Tenant ID
            current_user_id: Current user ID (for permission check)
            email: Email of user to invite
            role: Role to assign

        Returns:
            Message with invitation status

        Raises:
            AuthorizationError: If user doesn't have permission
            NotFoundError: If user not found
            AlreadyExistsError: If user already in tenant
        """
        # Check permission (owner or admin only)
        await self._check_user_permission(
            current_user_id,
            tenant_id,
            [TenantRole.OWNER, TenantRole.ADMIN],
        )

        # Find user by email
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError(f"User with email {email}")

        # Check if already in tenant
        result = await self.db.execute(
            select(UserTenant)
            .where(UserTenant.user_id == user.id)
            .where(UserTenant.tenant_id == tenant_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            raise AlreadyExistsError(f"User {email} in this tenant")

        # Add user to tenant
        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=tenant_id,
            role=role,
            is_default=False,
        )
        self.db.add(user_tenant)
        await self.db.commit()

        # TODO: Send invitation email

        return {
            "message": f"User {email} invited successfully",
            "user_id": str(user.id),
            "role": role.value,
        }

    async def update_user_role(
        self,
        tenant_id: UUID,
        current_user_id: UUID,
        target_user_id: UUID,
        new_role: TenantRole,
    ) -> dict:
        """
        Update user role in tenant

        Args:
            tenant_id: Tenant ID
            current_user_id: Current user ID (for permission check)
            target_user_id: User ID to update
            new_role: New role

        Returns:
            Updated user info

        Raises:
            AuthorizationError: If user doesn't have permission
            NotFoundError: If user not found in tenant
            ValidationError: If trying to change owner role
        """
        # Check permission (owner only)
        await self._check_user_permission(
            current_user_id,
            tenant_id,
            [TenantRole.OWNER],
        )

        # Get target user tenant
        result = await self.db.execute(
            select(UserTenant)
            .where(UserTenant.user_id == target_user_id)
            .where(UserTenant.tenant_id == tenant_id)
        )
        user_tenant = result.scalar_one_or_none()

        if not user_tenant:
            raise NotFoundError("User in this tenant")

        # Don't allow changing owner role
        if user_tenant.role == TenantRole.OWNER:
            raise ValidationError("Cannot change owner role")

        # Update role
        user_tenant.role = new_role
        await self.db.commit()

        return {
            "message": "User role updated successfully",
            "user_id": str(target_user_id),
            "new_role": new_role.value,
        }

    async def remove_user(
        self,
        tenant_id: UUID,
        current_user_id: UUID,
        target_user_id: UUID,
    ) -> dict:
        """
        Remove user from tenant

        Args:
            tenant_id: Tenant ID
            current_user_id: Current user ID (for permission check)
            target_user_id: User ID to remove

        Returns:
            Removal confirmation

        Raises:
            AuthorizationError: If user doesn't have permission
            NotFoundError: If user not found in tenant
            ValidationError: If trying to remove owner
        """
        # Check permission (owner or admin only)
        await self._check_user_permission(
            current_user_id,
            tenant_id,
            [TenantRole.OWNER, TenantRole.ADMIN],
        )

        # Get target user tenant
        result = await self.db.execute(
            select(UserTenant)
            .where(UserTenant.user_id == target_user_id)
            .where(UserTenant.tenant_id == tenant_id)
        )
        user_tenant = result.scalar_one_or_none()

        if not user_tenant:
            raise NotFoundError("User in this tenant")

        # Don't allow removing owner
        if user_tenant.role == TenantRole.OWNER:
            raise ValidationError("Cannot remove owner from tenant")

        # Don't allow removing yourself
        if target_user_id == current_user_id:
            raise ValidationError("Cannot remove yourself from tenant")

        # Remove user
        await self.db.delete(user_tenant)
        await self.db.commit()

        return {
            "message": "User removed from tenant successfully",
            "user_id": str(target_user_id),
        }

    # Helper methods

    async def _check_user_access(
        self,
        user_id: UUID,
        tenant_id: UUID,
    ) -> UserTenant:
        """Check if user has access to tenant"""
        result = await self.db.execute(
            select(UserTenant)
            .where(UserTenant.user_id == user_id)
            .where(UserTenant.tenant_id == tenant_id)
        )
        user_tenant = result.scalar_one_or_none()

        if not user_tenant:
            raise AuthorizationError("You don't have access to this tenant")

        return user_tenant

    async def _check_user_permission(
        self,
        user_id: UUID,
        tenant_id: UUID,
        allowed_roles: list[TenantRole],
    ) -> UserTenant:
        """Check if user has required role in tenant"""
        user_tenant = await self._check_user_access(user_id, tenant_id)

        if user_tenant.role not in allowed_roles:
            raise AuthorizationError(
                f"This action requires one of the following roles: "
                f"{', '.join(r.value for r in allowed_roles)}"
            )

        return user_tenant
