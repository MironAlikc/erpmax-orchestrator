"""Billing service - business logic for subscriptions and payments"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models import Plan, Subscription, PaymentEvent, Tenant, User
from app.models.enums import BillingPeriod, SubscriptionStatus, PaymentEventType
from app.services.stripe import StripeService


class BillingService:
    """Billing management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_active_plans(self) -> list[Plan]:
        result = await self.db.execute(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order.asc())
        )
        return list(result.scalars().all())

    async def get_current_subscription(self, tenant_id: UUID) -> Subscription:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.tenant_id == tenant_id)
            .options(selectinload(Subscription.plan))
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise NotFoundError("Subscription")
        return subscription

    async def list_payment_events(
        self,
        *,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PaymentEvent], int]:
        subscription = await self.get_current_subscription(tenant_id)

        total_result = await self.db.execute(
            select(func.count(PaymentEvent.id)).where(
                PaymentEvent.subscription_id == subscription.id
            )
        )
        total = int(total_result.scalar_one())

        result = await self.db.execute(
            select(PaymentEvent)
            .where(PaymentEvent.subscription_id == subscription.id)
            .order_by(PaymentEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        events = list(result.scalars().all())
        return events, total

    async def create_checkout(
        self,
        *,
        tenant: Tenant,
        user: User,
        plan_id: UUID,
        billing_period: BillingPeriod,
        payment_provider: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, str]:
        if payment_provider.lower() != "stripe":
            raise ValidationError(
                "Only 'stripe' payment provider is supported currently"
            )

        result = await self.db.execute(select(Plan).where(Plan.id == plan_id))
        plan = result.scalar_one_or_none()
        if not plan or not plan.is_active:
            raise NotFoundError("Plan")

        subscription = await self.get_current_subscription(tenant.id)

        amount_dec: Decimal = (
            plan.price_monthly
            if billing_period == BillingPeriod.MONTHLY
            else plan.price_yearly
        )
        amount = int((amount_dec * 100).to_integral_value())

        stripe = StripeService()
        customer_id = await stripe.create_customer_if_needed(
            email=user.email, external_customer_id=subscription.external_customer_id
        )

        session = await stripe.create_checkout_session(
            customer_id=customer_id,
            plan_name=plan.name,
            currency=plan.currency,
            amount=amount,
            billing_period=billing_period,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "tenant_id": str(tenant.id),
                "plan_id": str(plan.id),
                "billing_period": billing_period.value,
            },
        )

        subscription.payment_provider = "stripe"
        subscription.external_customer_id = customer_id
        await self.db.commit()

        return {"checkout_url": session.checkout_url, "session_id": session.session_id}

    async def cancel_subscription(
        self,
        *,
        tenant_id: UUID,
        reason: str | None,
        cancel_at_period_end: bool,
    ) -> Subscription:
        subscription = await self.get_current_subscription(tenant_id)

        subscription.cancel_reason = reason
        subscription.cancelled_at = datetime.utcnow()

        if (
            subscription.payment_provider == "stripe"
            and subscription.external_subscription_id
        ):
            stripe = StripeService()
            await stripe.cancel_subscription(
                external_subscription_id=subscription.external_subscription_id,
                at_period_end=cancel_at_period_end,
            )

        if cancel_at_period_end:
            subscription.status = SubscriptionStatus.CANCELLED
        else:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.current_period_end = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def handle_stripe_webhook(
        self, *, payload: bytes, signature_header: str
    ) -> None:
        stripe = StripeService()
        stripe.verify_webhook_signature(
            payload=payload, signature_header=signature_header
        )

        event = stripe.parse_event(payload)
        event_id = event.get("id")
        event_type = event.get("type")
        data_object = (event.get("data") or {}).get("object") or {}

        if not event_id or not event_type:
            raise ValidationError("Stripe event missing required fields")

        tenant_id_str = (data_object.get("metadata") or {}).get("tenant_id")
        if not tenant_id_str:
            return

        tenant_id = UUID(tenant_id_str)

        result = await self.db.execute(
            select(Subscription).where(Subscription.tenant_id == tenant_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            return

        existing = await self.db.execute(
            select(PaymentEvent).where(PaymentEvent.provider_event_id == event_id)
        )
        if existing.scalar_one_or_none():
            return

        payment_intent = data_object.get("payment_intent")
        stripe_subscription_id = data_object.get("subscription")
        stripe_customer_id = data_object.get("customer")

        if isinstance(stripe_subscription_id, str):
            subscription.external_subscription_id = stripe_subscription_id
        if isinstance(stripe_customer_id, str):
            subscription.external_customer_id = stripe_customer_id
        subscription.payment_provider = "stripe"

        mapped_event_type = None
        if event_type in {"invoice.paid", "checkout.session.completed"}:
            mapped_event_type = PaymentEventType.PAYMENT_SUCCESS
            subscription.status = SubscriptionStatus.ACTIVE
        elif event_type in {"invoice.payment_failed"}:
            mapped_event_type = PaymentEventType.PAYMENT_FAILED
            subscription.status = SubscriptionStatus.PAST_DUE

        if mapped_event_type:
            amount_paid = data_object.get("amount_paid")
            currency = data_object.get("currency")

            amount_dec = Decimal(0)
            if isinstance(amount_paid, int):
                amount_dec = Decimal(amount_paid) / Decimal(100)

            currency_str = str(currency).upper() if currency else "USD"

            payment_event = PaymentEvent(
                subscription_id=subscription.id,
                event_type=mapped_event_type,
                amount=amount_dec,
                currency=currency_str,
                provider_event_id=event_id,
                provider_payment_id=str(payment_intent) if payment_intent else None,
                event_metadata=event,
            )
            self.db.add(payment_event)

        await self.db.commit()
