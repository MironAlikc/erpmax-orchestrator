from __future__ import annotations

import hmac
import json
import logging
import uuid
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.models.enums import BillingPeriod

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StripeCheckoutSession:
    checkout_url: str
    session_id: str


class StripeService:
    def __init__(self) -> None:
        self._settings = get_settings()

    def _is_mock_mode(self) -> bool:
        """Check if we're in mock mode (for development without real Stripe keys)"""
        key = self._settings.stripe_secret_key
        return key is not None and (
            key.startswith("sk_test_mock_") or key == "sk_test_..." or key == "mock"
        )

    def _require_secret_key(self) -> str:
        if not self._settings.stripe_secret_key:
            raise ValidationError("Stripe secret key is not configured")
        return self._settings.stripe_secret_key

    async def create_customer_if_needed(
        self, *, email: str, external_customer_id: str | None
    ) -> str:
        if external_customer_id:
            return external_customer_id

        # Mock mode for development
        if self._is_mock_mode():
            customer_id = f"cus_mock_{uuid.uuid4().hex[:24]}"
            logger.info(
                f"[MOCK MODE] Created mock Stripe customer: {customer_id} for {email}"
            )
            return customer_id

        secret_key = self._require_secret_key()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.stripe.com/v1/customers",
                auth=(secret_key, ""),
                data={"email": email},
            )
            resp.raise_for_status()
            data = resp.json()
            customer_id = data.get("id")
            if not customer_id:
                raise ValidationError("Stripe customer creation failed")
            return customer_id

    async def create_checkout_session(
        self,
        *,
        customer_id: str,
        plan_name: str,
        currency: str,
        amount: int,
        billing_period: BillingPeriod,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
    ) -> StripeCheckoutSession:
        # Mock mode for development
        if self._is_mock_mode():
            session_id = f"cs_test_mock_{uuid.uuid4().hex[:40]}"
            checkout_url = f"https://checkout.stripe.com/mock/pay/{session_id}"
            logger.info(
                f"[MOCK MODE] Created mock checkout session: {session_id} "
                f"for plan '{plan_name}' ({amount/100:.2f} {currency})"
            )
            return StripeCheckoutSession(
                checkout_url=checkout_url, session_id=session_id
            )

        secret_key = self._require_secret_key()

        interval = "month" if billing_period == BillingPeriod.MONTHLY else "year"

        payload: dict[str, Any] = {
            "mode": "subscription",
            "customer": customer_id,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "line_items[0][quantity]": 1,
            "line_items[0][price_data][currency]": currency.lower(),
            "line_items[0][price_data][unit_amount]": amount,
            "line_items[0][price_data][product_data][name]": plan_name,
            "line_items[0][price_data][recurring][interval]": interval,
        }

        for key, value in metadata.items():
            payload[f"metadata[{key}]"] = value

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.stripe.com/v1/checkout/sessions",
                auth=(secret_key, ""),
                data=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        session_id = data.get("id")
        checkout_url = data.get("url")
        if not session_id or not checkout_url:
            raise ValidationError("Stripe checkout session creation failed")

        return StripeCheckoutSession(checkout_url=checkout_url, session_id=session_id)

    async def cancel_subscription(
        self, *, external_subscription_id: str, at_period_end: bool
    ) -> None:
        # Mock mode for development
        if self._is_mock_mode():
            logger.info(
                f"[MOCK MODE] Mock cancelled subscription: {external_subscription_id} "
                f"(at_period_end={at_period_end})"
            )
            return  # Mock cancellation - do nothing

        secret_key = self._require_secret_key()
        async with httpx.AsyncClient(timeout=30.0) as client:
            if at_period_end:
                resp = await client.post(
                    f"https://api.stripe.com/v1/subscriptions/{external_subscription_id}",
                    auth=(secret_key, ""),
                    data={"cancel_at_period_end": "true"},
                )
            else:
                resp = await client.delete(
                    f"https://api.stripe.com/v1/subscriptions/{external_subscription_id}",
                    auth=(secret_key, ""),
                )
            resp.raise_for_status()

    def verify_webhook_signature(
        self, *, payload: bytes, signature_header: str
    ) -> None:
        if not self._settings.stripe_webhook_secret:
            raise ValidationError("Stripe webhook secret is not configured")

        parts = [p.strip() for p in signature_header.split(",") if p.strip()]
        values: dict[str, str] = {}
        for part in parts:
            if "=" in part:
                k, v = part.split("=", 1)
                values[k] = v

        timestamp = values.get("t")
        signature = values.get("v1")
        if not timestamp or not signature:
            raise ValidationError("Invalid Stripe-Signature header")

        signed_payload = f"{timestamp}.".encode("utf-8") + payload
        expected = hmac.new(
            self._settings.stripe_webhook_secret.encode("utf-8"),
            signed_payload,
            sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise ValidationError("Invalid Stripe webhook signature")

    @staticmethod
    def parse_event(payload: bytes) -> dict[str, Any]:
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception as e:
            raise ValidationError("Invalid Stripe webhook payload") from e
