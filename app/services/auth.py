"""Authentication service - business logic for user authentication"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.core.exceptions import (
    AuthenticationError,
    AlreadyExistsError,
    NotFoundError,
    ValidationError,
)
from app.models import User, Tenant, UserTenant, Subscription, Plan
from app.models.enums import TenantRole, TenantStatus, SubscriptionStatus, BillingPeriod
from app.schemas.auth import RegisterRequest, LoginRequest
from app.schemas.user import UserResponse
from app.schemas.tenant import TenantResponse


class AuthService:
    """Authentication service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(
        self,
        data: RegisterRequest,
    ) -> tuple[User, Tenant, dict[str, str]]:
        """
        Register new user with tenant and trial subscription

        Creates:
        - User
        - Tenant (from company_name)
        - UserTenant (role=owner)
        - Subscription (trial)

        Args:
            data: Registration data

        Returns:
            Tuple of (user, tenant, tokens)

        Raises:
            AlreadyExistsError: If email already exists
        """
        # Check if user exists
        result = await self.db.execute(select(User).where(User.email == data.email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise AlreadyExistsError("User with this email")

        # Create user
        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            is_active=True,
            is_superuser=False,
        )
        self.db.add(user)
        await self.db.flush()

        # Create tenant (slug from company name)
        slug = self._generate_slug(data.company_name)
        tenant = Tenant(
            name=data.company_name,
            slug=slug,
            status=TenantStatus.PROVISIONING,
        )
        self.db.add(tenant)
        await self.db.flush()

        # Create user-tenant relationship
        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=tenant.id,
            role=TenantRole.OWNER,
            is_default=True,
        )
        self.db.add(user_tenant)

        # Get trial plan
        trial_plan = await self._get_trial_plan()

        # Create trial subscription
        subscription = Subscription(
            tenant_id=tenant.id,
            plan_id=trial_plan.id,
            status=SubscriptionStatus.TRIAL,
            billing_period=BillingPeriod.MONTHLY,
            trial_ends_at=datetime.utcnow() + timedelta(days=14),
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=14),
        )
        self.db.add(subscription)

        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(tenant)

        # Generate tokens
        tokens = self._generate_tokens(user.id, tenant.id)

        # TODO: Trigger provisioning job via RabbitMQ

        return user, tenant, tokens

    async def login(
        self,
        data: LoginRequest,
    ) -> tuple[User, list[dict], Optional[Tenant], dict[str, str]]:
        """
        Authenticate user and return tokens

        Args:
            data: Login credentials

        Returns:
            Tuple of (user, tenants, default_tenant, tokens)

        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Get user with tenants
        result = await self.db.execute(
            select(User)
            .where(User.email == data.email)
            .options(selectinload(User.user_tenants))
        )
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError("Invalid email or password")

        # Verify password
        if not verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        # Get user's tenants
        tenants_data = await self._get_user_tenants(user.id)

        if not tenants_data:
            raise AuthenticationError("User has no tenants")

        # Get default tenant
        default_tenant = None
        default_tenant_id = None

        for tenant_info in tenants_data:
            if tenant_info["is_default"]:
                default_tenant_id = tenant_info["tenant_id"]
                break

        if not default_tenant_id and tenants_data:
            default_tenant_id = tenants_data[0]["tenant_id"]

        if default_tenant_id:
            result = await self.db.execute(
                select(Tenant).where(Tenant.id == default_tenant_id)
            )
            default_tenant = result.scalar_one_or_none()

        # Generate tokens with default tenant
        tokens = self._generate_tokens(user.id, default_tenant_id)

        return user, tenants_data, default_tenant, tokens

    async def refresh_tokens(
        self,
        refresh_token: str,
    ) -> dict[str, str]:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Valid refresh token

        Returns:
            New tokens dict

        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            payload = verify_token(refresh_token, token_type="refresh")
            user_id = UUID(payload["sub"])
        except Exception:
            raise AuthenticationError("Invalid refresh token")

        # Verify user exists and is active
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        # Get user's default tenant
        tenants_data = await self._get_user_tenants(user.id)
        default_tenant_id = None

        for tenant_info in tenants_data:
            if tenant_info["is_default"]:
                default_tenant_id = tenant_info["tenant_id"]
                break

        if not default_tenant_id and tenants_data:
            default_tenant_id = tenants_data[0]["tenant_id"]

        # Generate new tokens
        tokens = self._generate_tokens(user.id, default_tenant_id)

        return tokens

    async def switch_tenant(
        self,
        user_id: UUID,
        tenant_id: UUID,
    ) -> tuple[Tenant, dict[str, str]]:
        """
        Switch user's current tenant

        Args:
            user_id: User ID
            tenant_id: Target tenant ID

        Returns:
            Tuple of (tenant, new_tokens)

        Raises:
            NotFoundError: If tenant not found
            AuthenticationError: If user doesn't have access
        """
        # Verify user has access to tenant
        result = await self.db.execute(
            select(UserTenant)
            .where(UserTenant.user_id == user_id)
            .where(UserTenant.tenant_id == tenant_id)
        )
        user_tenant = result.scalar_one_or_none()

        if not user_tenant:
            raise AuthenticationError("You don't have access to this tenant")

        # Get tenant
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise NotFoundError("Tenant")

        # Update default tenant
        await self.db.execute(select(UserTenant).where(UserTenant.user_id == user_id))

        # Set all to non-default
        result = await self.db.execute(
            select(UserTenant).where(UserTenant.user_id == user_id)
        )
        all_user_tenants = result.scalars().all()

        for ut in all_user_tenants:
            ut.is_default = ut.tenant_id == tenant_id

        await self.db.commit()

        # Generate new tokens with new tenant
        tokens = self._generate_tokens(user_id, tenant_id)

        return tenant, tokens

    async def get_current_user_info(
        self,
        user_id: UUID,
    ) -> tuple[User, list[dict], Optional[Tenant]]:
        """
        Get current user info with tenants

        Args:
            user_id: User ID

        Returns:
            Tuple of (user, tenants, current_tenant)
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("User")

        # Get user's tenants
        tenants_data = await self._get_user_tenants(user.id)

        # Get current/default tenant
        current_tenant = None
        for tenant_info in tenants_data:
            if tenant_info["is_default"]:
                result = await self.db.execute(
                    select(Tenant).where(Tenant.id == tenant_info["tenant_id"])
                )
                current_tenant = result.scalar_one_or_none()
                break

        return user, tenants_data, current_tenant

    # Helper methods

    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from name"""
        import re

        slug = name.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        slug = slug.strip("-")
        return slug[:100]

    async def _get_trial_plan(self) -> Plan:
        """Get trial plan (or create if not exists)"""
        result = await self.db.execute(select(Plan).where(Plan.slug == "trial"))
        plan = result.scalar_one_or_none()

        if not plan:
            # Create trial plan
            plan = Plan(
                name="Trial",
                slug="trial",
                description="14-day free trial",
                price_monthly=0,
                price_yearly=0,
                currency="USD",
                limits={"users": 3, "storage_gb": 10},
                features=["Basic features", "Email support"],
                is_active=True,
                sort_order=0,
            )
            self.db.add(plan)
            await self.db.flush()

        return plan

    async def _get_user_tenants(self, user_id: UUID) -> list[dict]:
        """Get user's tenants with roles"""
        result = await self.db.execute(
            select(UserTenant, Tenant)
            .join(Tenant, UserTenant.tenant_id == Tenant.id)
            .where(UserTenant.user_id == user_id)
        )

        tenants_data = []
        for user_tenant, tenant in result.all():
            tenants_data.append(
                {
                    "tenant_id": str(tenant.id),
                    "tenant_name": tenant.name,
                    "role": user_tenant.role.value,
                    "is_default": user_tenant.is_default,
                }
            )

        return tenants_data

    def _generate_tokens(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
    ) -> dict[str, str]:
        """Generate access and refresh tokens"""
        access_token = create_access_token(
            subject=user_id,
            tenant_id=tenant_id,
        )

        refresh_token = create_refresh_token(
            subject=user_id,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
