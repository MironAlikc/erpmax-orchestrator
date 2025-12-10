from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import EmailStr, Field, field_validator

from app.schemas.base import BaseSchema


class UserBase(BaseSchema):
    """Base user schema with common fields"""

    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(
        ..., min_length=1, max_length=255, description="User full name"
    )


class UserCreate(UserBase):
    """Schema for creating a new user"""

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User password (min 8 characters)",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        return v


class UserUpdate(BaseSchema):
    """Schema for updating user"""

    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None


class UserResponse(UserBase):
    """Schema for user response"""

    id: UUID = Field(..., description="User unique identifier")
    is_active: bool = Field(..., description="User active status")
    is_superuser: bool = Field(False, description="Superuser status")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="User last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }


class UserWithTenants(UserResponse):
    """User response with tenant information"""

    tenants: list[dict] = Field(
        default_factory=list, description="List of user's tenants with roles"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "tenants": [
                    {
                        "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                        "tenant_name": "My Company",
                        "role": "owner",
                        "is_default": True,
                    }
                ],
            }
        }
