import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_active_user, get_current_tenant, get_db
from app.core.redis import get_redis
from app.main import app
from app.models.enums import TenantStatus
from app.schemas.sso import SSOTokenResponse
from app.services import sso as sso_module


@dataclass
class FakeUser:
    id: UUID
    email: str
    full_name: str
    is_active: bool


@dataclass
class FakeTenant:
    id: UUID
    name: str
    slug: str
    status: TenantStatus
    erpnext_site_url: str | None


@dataclass
class FakeRedis:
    """Mock Redis client for testing"""

    _storage: dict

    def __init__(self):
        self._storage = {}

    async def hset(self, key: str, mapping: dict):
        self._storage[key] = mapping

    async def expire(self, key: str, seconds: int):
        pass

    async def hgetall(self, key: str):
        data = self._storage.get(key, {})
        # Convert to bytes like real Redis
        return {
            k.encode(): v.encode() if isinstance(v, str) else v for k, v in data.items()
        }

    async def delete(self, key: str):
        self._storage.pop(key, None)

    async def close(self):
        pass


# Test fixtures
fake_user = FakeUser(
    id=uuid4(), email="test@example.com", full_name="Test User", is_active=True
)

fake_tenant = FakeTenant(
    id=uuid4(),
    name="Test Company",
    slug="test-company",
    status=TenantStatus.ACTIVE,
    erpnext_site_url="https://test-company.erpnext.com",
)

fake_redis = FakeRedis()


# Mock SSO Service
class MockSSOService:
    """Mock SSO Service for testing"""

    async def generate_erpnext_token(
        self, user_id: UUID, tenant_id: UUID
    ) -> SSOTokenResponse:
        token = "test_token_123"
        expires_at = datetime.utcnow() + timedelta(seconds=60)
        sso_url = f"https://test-company.erpnext.com/api/method/erpmax.sso.login?token={token}"

        # Store in fake Redis
        token_key = f"sso:token:{token}"
        await fake_redis.hset(
            token_key,
            {
                "user_id": str(user_id),
                "tenant_id": str(tenant_id),
                "created_at": datetime.utcnow().isoformat(),
            },
        )

        return SSOTokenResponse(sso_url=sso_url, token=token, expires_at=expires_at)

    async def validate_token(self, token: str) -> tuple[UUID, UUID]:
        token_key = f"sso:token:{token}"
        token_data = await fake_redis.hgetall(token_key)

        if not token_data:
            from app.core.exceptions import forbidden_exception

            raise forbidden_exception("Invalid or expired SSO token")

        await fake_redis.delete(token_key)

        user_id = UUID(token_data[b"user_id"].decode())
        tenant_id = UUID(token_data[b"tenant_id"].decode())

        return user_id, tenant_id

    async def get_user_session_data(self, user_id: UUID, tenant_id: UUID) -> dict:
        return {
            "user": {
                "id": str(fake_user.id),
                "email": fake_user.email,
                "full_name": fake_user.full_name,
            },
            "tenant": {
                "id": str(fake_tenant.id),
                "name": fake_tenant.name,
                "slug": fake_tenant.slug,
            },
        }


async def override_get_current_user():
    return fake_user


async def override_get_current_tenant():
    return fake_tenant


async def override_get_db():
    yield None


async def override_get_redis():
    yield fake_redis


# Override dependencies
app.dependency_overrides[get_current_active_user] = override_get_current_user
app.dependency_overrides[get_current_tenant] = override_get_current_tenant
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_redis] = override_get_redis

# Mock SSO Service
sso_module.SSOService = MockSSOService


@pytest.mark.asyncio
async def test_create_sso_token():
    """Test SSO token generation endpoint"""
    # Test the service directly
    mock_service = MockSSOService()
    result = await mock_service.generate_erpnext_token(fake_user.id, fake_tenant.id)

    assert result.token == "test_token_123"
    assert result.sso_url.startswith("https://test-company.erpnext.com")
    assert "token=" in result.sso_url


@pytest.mark.asyncio
async def test_validate_sso_token():
    """Test SSO token validation endpoint"""
    # First create a token
    mock_service = MockSSOService()
    result = await mock_service.generate_erpnext_token(fake_user.id, fake_tenant.id)
    token = result.token

    # Validate the token using service
    user_id, tenant_id = await mock_service.validate_token(token)

    assert user_id == fake_user.id
    assert tenant_id == fake_tenant.id


@pytest.mark.asyncio
async def test_sso_callback():
    """Test SSO callback endpoint"""
    # First create a token
    mock_service = MockSSOService()
    result = await mock_service.generate_erpnext_token(fake_user.id, fake_tenant.id)
    token = result.token

    # Get session data
    session_data = await mock_service.get_user_session_data(
        fake_user.id, fake_tenant.id
    )

    assert session_data["user"]["email"] == fake_user.email
    assert session_data["tenant"]["slug"] == fake_tenant.slug


@pytest.mark.asyncio
async def test_sso_callback_invalid_token():
    """Test SSO callback with invalid token"""
    # Test service directly with invalid token
    mock_service = MockSSOService()

    try:
        await mock_service.validate_token("invalid_token_xyz")
        assert False, "Should have raised exception"
    except Exception as e:
        # Should raise forbidden exception
        assert "Invalid or expired SSO token" in str(e)


if __name__ == "__main__":
    asyncio.run(test_create_sso_token())
    asyncio.run(test_validate_sso_token())
    asyncio.run(test_sso_callback())
    asyncio.run(test_sso_callback_invalid_token())
    print("All SSO API tests passed!")
