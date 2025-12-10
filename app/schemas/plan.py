from datetime import datetime
from uuid import UUID
from decimal import Decimal
from typing import Optional
from pydantic import Field

from app.schemas.base import BaseSchema


class PlanResponse(BaseSchema):
    """Schema for plan response"""

    id: UUID = Field(..., description="Plan unique identifier")
    name: str = Field(..., description="Plan name")
    slug: str = Field(..., description="Plan slug")
    description: Optional[str] = Field(None, description="Plan description")
    price_monthly: Decimal = Field(..., description="Monthly price")
    price_yearly: Decimal = Field(..., description="Yearly price")
    currency: str = Field(..., description="Currency code (ISO 4217)")
    limits: dict = Field(..., description="Plan limits (users, storage, etc.)")
    features: list = Field(..., description="List of plan features")
    is_active: bool = Field(..., description="Is plan available for subscription")
    sort_order: int = Field(..., description="Display order")
    created_at: datetime = Field(..., description="Plan creation timestamp")
    updated_at: datetime = Field(..., description="Plan last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Professional",
                "slug": "professional",
                "description": "Perfect for growing businesses",
                "price_monthly": "49.99",
                "price_yearly": "499.99",
                "currency": "USD",
                "limits": {
                    "users": 10,
                    "storage_gb": 100,
                    "api_calls_per_month": 100000,
                },
                "features": [
                    "Unlimited invoices",
                    "Advanced reporting",
                    "Priority support",
                    "API access",
                ],
                "is_active": True,
                "sort_order": 2,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }
