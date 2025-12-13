import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_active_user, get_current_tenant, get_db
from app.main import app
from app.models.enums import BillingPeriod, SubscriptionStatus
from app.services import billing as billing_module


@dataclass
class FakePlan:
    id: UUID
    name: str
    slug: str
    description: str | None
    price_monthly: Decimal
    price_yearly: Decimal
    currency: str
    limits: dict
    features: list
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


@dataclass
class FakeSubscription:
    id: UUID
    tenant_id: UUID
    plan_id: UUID
    status: SubscriptionStatus
    billing_period: BillingPeriod
    trial_ends_at: datetime | None
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: datetime | None
    cancel_reason: str | None
    payment_provider: str | None
    external_subscription_id: str | None
    external_customer_id: str | None
    created_at: datetime
    updated_at: datetime
    plan: FakePlan


@dataclass
class FakeUser:
    id: UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool


@dataclass
class FakeTenant:
    id: UUID
    name: str
    slug: str


async def _fake_db():
    yield None


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_list_plans_smoke():
    now = datetime.utcnow()

    fake_plan = FakePlan(
        id=uuid4(),
        name="Trial",
        slug="trial",
        description=None,
        price_monthly=Decimal("0"),
        price_yearly=Decimal("0"),
        currency="USD",
        limits={"users": 3},
        features=["Basic"],
        is_active=True,
        sort_order=0,
        created_at=now,
        updated_at=now,
    )

    async def _list_active_plans(self):
        return [fake_plan]

    billing_module.BillingService.list_active_plans = _list_active_plans  # type: ignore[method-assign]
    app.dependency_overrides[get_db] = _fake_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/billing/plans")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 1
    assert body["data"][0]["slug"] == "trial"


@pytest.mark.asyncio
async def test_get_subscription_smoke():
    now = datetime.utcnow()

    tenant_id = uuid4()
    plan_id = uuid4()
    sub_id = uuid4()

    fake_plan = FakePlan(
        id=plan_id,
        name="Trial",
        slug="trial",
        description=None,
        price_monthly=Decimal("0"),
        price_yearly=Decimal("0"),
        currency="USD",
        limits={"users": 3},
        features=["Basic"],
        is_active=True,
        sort_order=0,
        created_at=now,
        updated_at=now,
    )

    fake_subscription = FakeSubscription(
        id=sub_id,
        tenant_id=tenant_id,
        plan_id=plan_id,
        status=SubscriptionStatus.TRIAL,
        billing_period=BillingPeriod.MONTHLY,
        trial_ends_at=None,
        current_period_start=now,
        current_period_end=now,
        cancelled_at=None,
        cancel_reason=None,
        payment_provider=None,
        external_subscription_id=None,
        external_customer_id=None,
        created_at=now,
        updated_at=now,
        plan=fake_plan,
    )

    async def _get_current_subscription(self, _tenant_id):
        return fake_subscription

    billing_module.BillingService.get_current_subscription = _get_current_subscription  # type: ignore[method-assign]

    async def _get_user():
        return FakeUser(
            id=uuid4(),
            email="user@example.com",
            full_name="User",
            is_active=True,
            is_superuser=False,
        )

    async def _get_tenant():
        return FakeTenant(id=tenant_id, name="Tenant", slug="tenant")

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_active_user] = _get_user
    app.dependency_overrides[get_current_tenant] = _get_tenant

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/billing/subscription", headers={"Authorization": "Bearer test"}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["status"] == "trial"
    assert body["data"]["plan"]["id"] == str(plan_id)
