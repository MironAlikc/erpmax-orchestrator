#!/usr/bin/env python3
"""Test security functions"""

from uuid import uuid4
from datetime import timedelta

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_password_reset_token,
    verify_password_reset_token,
)


def test_password_hashing():
    """Test password hashing and verification"""
    print("\n🔐 Testing password hashing...")

    password = "SecurePassword123!"
    hashed = hash_password(password)

    print(f"   Original: {password}")
    print(f"   Hashed: {hashed[:50]}...")

    # Verify correct password
    assert verify_password(password, hashed), "❌ Password verification failed"
    print("   ✅ Correct password verified")

    # Verify wrong password
    assert not verify_password("WrongPassword", hashed), "❌ Wrong password accepted"
    print("   ✅ Wrong password rejected")


def test_jwt_tokens():
    """Test JWT token creation and verification"""
    print("\n🎫 Testing JWT tokens...")

    user_id = uuid4()
    tenant_id = uuid4()

    # Create access token
    access_token = create_access_token(
        subject=user_id,
        tenant_id=tenant_id,
        expires_delta=timedelta(minutes=30),
    )
    print(f"   Access token: {access_token[:50]}...")

    # Verify access token
    payload = verify_token(access_token, token_type="access")
    assert payload["sub"] == str(user_id), "❌ User ID mismatch"
    assert payload["tenant_id"] == str(tenant_id), "❌ Tenant ID mismatch"
    assert payload["type"] == "access", "❌ Token type mismatch"
    print("   ✅ Access token verified")

    # Create refresh token
    refresh_token = create_refresh_token(
        subject=user_id,
        expires_delta=timedelta(days=7),
    )
    print(f"   Refresh token: {refresh_token[:50]}...")

    # Verify refresh token
    payload = verify_token(refresh_token, token_type="refresh")
    assert payload["sub"] == str(user_id), "❌ User ID mismatch"
    assert payload["type"] == "refresh", "❌ Token type mismatch"
    print("   ✅ Refresh token verified")

    # Test wrong token type
    try:
        verify_token(access_token, token_type="refresh")
        print("   ❌ Should have rejected wrong token type")
    except Exception:
        print("   ✅ Wrong token type rejected")


def test_password_reset_token():
    """Test password reset token"""
    print("\n🔑 Testing password reset token...")

    email = "user@example.com"

    # Generate reset token
    reset_token = generate_password_reset_token(email)
    print(f"   Reset token: {reset_token[:50]}...")

    # Verify reset token
    verified_email = verify_password_reset_token(reset_token)
    assert verified_email == email, "❌ Email mismatch"
    print(f"   ✅ Reset token verified for: {verified_email}")

    # Test invalid token
    invalid_email = verify_password_reset_token("invalid_token")
    assert invalid_email is None, "❌ Invalid token should return None"
    print("   ✅ Invalid token rejected")


def test_additional_claims():
    """Test JWT with additional claims"""
    print("\n📋 Testing additional claims...")

    user_id = uuid4()
    additional_claims = {
        "role": "admin",
        "permissions": ["read", "write"],
    }

    token = create_access_token(
        subject=user_id,
        additional_claims=additional_claims,
    )

    payload = verify_token(token, token_type="access")
    assert payload["role"] == "admin", "❌ Role claim missing"
    assert payload["permissions"] == ["read", "write"], "❌ Permissions claim missing"
    print("   ✅ Additional claims verified")


def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Testing Security Functions")
    print("=" * 60)

    try:
        test_password_hashing()
        test_jwt_tokens()
        test_password_reset_token()
        test_additional_claims()

        print("\n" + "=" * 60)
        print("✅ All security tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
