from uuid import UUID
from typing import Optional
from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema
from app.schemas.user import UserResponse
from app.schemas.tenant import TenantResponse


class Token(BaseSchema):
    """JWT token response"""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }


class LoginRequest(BaseSchema):
    """Login request schema"""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")

    class Config:
        json_schema_extra = {
            "example": {"email": "user@example.com", "password": "SecurePass123"}
        }


class LoginResponse(Token):
    """Login response with user and tenant info"""

    user: UserResponse = Field(..., description="User information")
    tenants: list[dict] = Field(..., description="User's tenants with roles")
    current_tenant: Optional[TenantResponse] = Field(
        None, description="Current active tenant"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "is_active": True,
                    "is_superuser": False,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
                "tenants": [
                    {
                        "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                        "tenant_name": "My Company",
                        "role": "owner",
                        "is_default": True,
                    }
                ],
                "current_tenant": {
                    "id": "123e4567-e89b-12d3-a456-426614174001",
                    "name": "My Company",
                    "slug": "my-company",
                    "status": "active",
                    "erpnext_site_url": "https://my-company.erpnext.com",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
            }
        }


class RegisterRequest(BaseSchema):
    """Registration request schema"""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")
    full_name: str = Field(
        ..., min_length=1, max_length=255, description="User full name"
    )
    company_name: str = Field(
        ..., min_length=1, max_length=255, description="Company name"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123",
                "full_name": "John Doe",
                "company_name": "My Company",
            }
        }


class RegisterResponse(LoginResponse):
    """Registration response (same as login)"""

    pass


class RefreshTokenRequest(BaseSchema):
    """Refresh token request"""

    refresh_token: str = Field(..., description="Refresh token")

    class Config:
        json_schema_extra = {
            "example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
        }


class SwitchTenantRequest(BaseSchema):
    """Switch tenant request"""

    tenant_id: UUID = Field(..., description="Tenant ID to switch to")

    class Config:
        json_schema_extra = {
            "example": {"tenant_id": "123e4567-e89b-12d3-a456-426614174001"}
        }


class SwitchTenantResponse(Token):
    """Switch tenant response with new tokens"""

    tenant: TenantResponse = Field(..., description="New current tenant")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "tenant": {
                    "id": "123e4567-e89b-12d3-a456-426614174001",
                    "name": "My Company",
                    "slug": "my-company",
                    "status": "active",
                    "erpnext_site_url": None,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
            }
        }


class ForgotPasswordRequest(BaseSchema):
    """Forgot password request"""

    email: EmailStr = Field(..., description="User email")

    class Config:
        json_schema_extra = {"example": {"email": "user@example.com"}}


class ResetPasswordRequest(BaseSchema):
    """Reset password request"""

    token: str = Field(..., description="Reset token from email")
    new_password: str = Field(..., min_length=8, description="New password")

    class Config:
        json_schema_extra = {
            "example": {"token": "reset_token_here", "new_password": "NewSecurePass123"}
        }
