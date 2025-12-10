from datetime import datetime
from uuid import UUID
from decimal import Decimal
from typing import Optional
from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.plan import PlanResponse
from app.models.enums import SubscriptionStatus, BillingPeriod, PaymentEventType


class SubscriptionResponse(BaseSchema):
    """Schema for subscription response"""

    id: UUID = Field(..., description="Subscription unique identifier")
    tenant_id: UUID = Field(..., description="Tenant ID")
    plan_id: UUID = Field(..., description="Plan ID")
    status: SubscriptionStatus = Field(..., description="Subscription status")
    billing_period: BillingPeriod = Field(..., description="Billing period")
    trial_ends_at: Optional[datetime] = Field(None, description="Trial end date")
    current_period_start: datetime = Field(
        ..., description="Current billing period start"
    )
    current_period_end: datetime = Field(..., description="Current billing period end")
    cancelled_at: Optional[datetime] = Field(None, description="Cancellation date")
    cancel_reason: Optional[str] = Field(None, description="Cancellation reason")
    payment_provider: Optional[str] = Field(
        None, description="Payment provider (stripe, liqpay)"
    )
    external_subscription_id: Optional[str] = Field(
        None, description="External subscription ID"
    )
    external_customer_id: Optional[str] = Field(
        None, description="External customer ID"
    )
    created_at: datetime = Field(..., description="Subscription creation timestamp")
    updated_at: datetime = Field(..., description="Subscription last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "plan_id": "123e4567-e89b-12d3-a456-426614174002",
                "status": "active",
                "billing_period": "monthly",
                "trial_ends_at": None,
                "current_period_start": "2024-01-01T00:00:00Z",
                "current_period_end": "2024-02-01T00:00:00Z",
                "cancelled_at": None,
                "cancel_reason": None,
                "payment_provider": "stripe",
                "external_subscription_id": "sub_1234567890",
                "external_customer_id": "cus_1234567890",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }


class SubscriptionWithPlan(SubscriptionResponse):
    """Subscription response with plan details"""

    plan: PlanResponse = Field(..., description="Plan details")


class CheckoutRequest(BaseSchema):
    """Schema for creating checkout session"""

    plan_id: UUID = Field(..., description="Plan ID to subscribe to")
    billing_period: BillingPeriod = Field(..., description="Billing period")
    payment_provider: str = Field(..., description="Payment provider (stripe, liqpay)")
    success_url: str = Field(..., description="Success redirect URL")
    cancel_url: str = Field(..., description="Cancel redirect URL")

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "123e4567-e89b-12d3-a456-426614174000",
                "billing_period": "monthly",
                "payment_provider": "stripe",
                "success_url": "https://app.example.com/billing/success",
                "cancel_url": "https://app.example.com/billing/cancel",
            }
        }


class CheckoutResponse(BaseSchema):
    """Schema for checkout session response"""

    checkout_url: str = Field(..., description="URL to redirect user for payment")
    session_id: str = Field(..., description="Checkout session ID")

    class Config:
        json_schema_extra = {
            "example": {
                "checkout_url": "https://checkout.stripe.com/pay/cs_test_...",
                "session_id": "cs_test_1234567890",
            }
        }


class CancelSubscriptionRequest(BaseSchema):
    """Schema for cancelling subscription"""

    reason: Optional[str] = Field(
        None, max_length=500, description="Cancellation reason"
    )
    cancel_at_period_end: bool = Field(
        True, description="Cancel at end of current period or immediately"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Switching to another provider",
                "cancel_at_period_end": True,
            }
        }


class PaymentEventResponse(BaseSchema):
    """Schema for payment event response"""

    id: UUID = Field(..., description="Payment event unique identifier")
    subscription_id: UUID = Field(..., description="Subscription ID")
    event_type: PaymentEventType = Field(..., description="Event type")
    amount: Decimal = Field(..., description="Amount")
    currency: str = Field(..., description="Currency code")
    provider_event_id: str = Field(..., description="Provider event ID")
    provider_payment_id: Optional[str] = Field(None, description="Provider payment ID")
    event_metadata: dict = Field(..., description="Raw webhook data")
    created_at: datetime = Field(..., description="Event timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "subscription_id": "123e4567-e89b-12d3-a456-426614174001",
                "event_type": "payment_success",
                "amount": "49.99",
                "currency": "USD",
                "provider_event_id": "evt_1234567890",
                "provider_payment_id": "pi_1234567890",
                "event_metadata": {},
                "created_at": "2024-01-01T00:00:00Z",
            }
        }
