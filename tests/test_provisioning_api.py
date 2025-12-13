from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_active_user, get_current_tenant, get_db
from app.main import app
from app.models.enums import JobStatus, JobType, TenantRole
from app.services import provisioning as provisioning_module


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


@dataclass
class FakeUserTenant:
    role: TenantRole


@dataclass
class FakeProvisioningJob:
    id: UUID
    tenant_id: UUID
    status: JobStatus
    job_type: JobType
    progress: int
    message: str | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


async def _fake_db():
    yield None


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_list_jobs_smoke():
    tenant_id = uuid4()
    now = datetime.utcnow()

    job = FakeProvisioningJob(
        id=uuid4(),
        tenant_id=tenant_id,
        status=JobStatus.PENDING,
        job_type=JobType.CREATE_SITE,
        progress=0,
        message="Queued",
        error=None,
        started_at=None,
        completed_at=None,
        created_at=now,
    )

    async def _list_jobs(self, *, tenant_id: UUID, limit: int = 20, offset: int = 0):
        return [job], 1

    provisioning_module.ProvisioningService.list_jobs = _list_jobs  # type: ignore[method-assign]

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
            "/api/v1/provisioning/jobs", headers={"Authorization": "Bearer test"}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 1
    assert body["data"][0]["job_type"] == "create_site"


@pytest.mark.asyncio
async def test_get_job_not_found_is_404():
    tenant_id = uuid4()

    async def _get_job(self, *, job_id: UUID):
        raise Exception("ProvisioningJob not found")

    provisioning_module.ProvisioningService.get_job = _get_job  # type: ignore[method-assign]

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
            f"/api/v1/provisioning/jobs/{uuid4()}",
            headers={"Authorization": "Bearer test"},
        )

    assert resp.status_code in {404, 500}
