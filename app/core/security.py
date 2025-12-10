from datetime import datetime, timedelta
from typing import Optional, Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"


def create_access_token(
    subject: str | UUID,
    tenant_id: Optional[str | UUID] = None,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    """
    Create JWT access token

    Args:
        subject: User ID
        tenant_id: Current tenant ID (optional)
        expires_delta: Token expiration time (optional)
        additional_claims: Additional claims to include (optional)

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
    }

    if tenant_id:
        to_encode["tenant_id"] = str(tenant_id)

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: str | UUID,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT refresh token

    Args:
        subject: User ID
        expires_delta: Token expiration time (optional)

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> dict[str, Any]:
    """
    Verify and decode JWT token

    Args:
        token: JWT token to verify
        token_type: Expected token type (access or refresh)

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])

        # Verify token type
        if payload.get("type") != token_type:
            raise JWTError(f"Invalid token type. Expected {token_type}")

        return payload
    except JWTError as e:
        raise JWTError(f"Could not validate credentials: {str(e)}")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_password_reset_token(email: str) -> str:
    """
    Generate password reset token

    Args:
        email: User email

    Returns:
        Encoded JWT token for password reset
    """
    delta = timedelta(hours=settings.password_reset_token_expire_hours)
    now = datetime.utcnow()
    expires = now + delta

    to_encode = {
        "exp": expires,
        "nbf": now,
        "sub": email,
        "type": "password_reset",
    }

    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify password reset token

    Args:
        token: Password reset token

    Returns:
        Email if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])

        if payload.get("type") != "password_reset":
            return None

        email: str = payload.get("sub")
        return email
    except JWTError:
        return None
