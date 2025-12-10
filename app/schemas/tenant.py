from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import Field, field_validator
import re

from app.schemas.base import BaseSchema
from app.models.enums import TenantStatus, TenantRole


class TenantBase(BaseSchema):
    """Base tenant schema"""

    name: str = Field(..., min_length=1, max_length=255, description="Tenant name")
    slug: Optional[str] = Field(
        None, min_length=3, max_length=100, description="Tenant slug (URL-friendly)"
    )


class TenantCreate(TenantBase):
    """Schema for creating a new tenant"""

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        """Validate slug format"""
        if v is not None:
            if not re.match(r"^[a-z0-9-]+$", v):
                raise ValueError(
                    "Slug must contain only lowercase letters, numbers, and hyphens"
                )
            if v.startswith("-") or v.endswith("-"):
                raise ValueError("Slug cannot start or end with a hyphen")
        return v


class TenantUpdate(BaseSchema):
    """Schema for updating tenant"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    settings: Optional[dict] = Field(None, description="Tenant settings (JSON)")


class TenantResponse(TenantBase):
    """Schema for tenant response"""

    id: UUID = Field(..., description="Tenant unique identifier")
    slug: str = Field(..., description="Tenant slug")
    status: TenantStatus = Field(..., description="Tenant status")
    erpnext_site_url: Optional[str] = Field(None, description="ERPNext site URL")
    created_at: datetime = Field(..., description="Tenant creation timestamp")
    updated_at: datetime = Field(..., description="Tenant last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "My Company",
                "slug": "my-company",
                "status": "active",
                "erpnext_site_url": "https://my-company.erpnext.com",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }


class TenantWithSubscription(TenantResponse):
    """Tenant response with subscription details"""

    from app.schemas.subscription import SubscriptionResponse

    subscription: Optional["SubscriptionResponse"] = Field(
        None, description="Current subscription"
    )


class TenantUserResponse(BaseSchema):
    """Schema for tenant user (member)"""

    user_id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    role: TenantRole = Field(..., description="User role in tenant")
    is_default: bool = Field(..., description="Is this user's default tenant")
    joined_at: datetime = Field(..., description="When user joined the tenant")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "role": "admin",
                "is_default": True,
                "joined_at": "2024-01-01T00:00:00Z",
            }
        }


class TenantInviteRequest(BaseSchema):
    """Schema for inviting user to tenant"""

    email: str = Field(..., description="Email of user to invite")
    role: TenantRole = Field(TenantRole.USER, description="Role to assign")

    class Config:
        json_schema_extra = {
            "example": {"email": "newuser@example.com", "role": "user"}
        }


class TenantUserUpdateRole(BaseSchema):
    """Schema for updating user role in tenant"""

    role: TenantRole = Field(..., description="New role")

    class Config:
        json_schema_extra = {"example": {"role": "admin"}}
