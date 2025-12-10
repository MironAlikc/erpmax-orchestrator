from typing import Any, Optional
from fastapi import HTTPException, status


class ERPMaxException(Exception):
    """Base exception for ERPMax Orchestrator"""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(ERPMaxException):
    """Authentication failed"""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, code="AUTH_ERROR", **kwargs)


class AuthorizationError(ERPMaxException):
    """Authorization failed - user doesn't have permission"""

    def __init__(self, message: str = "Permission denied", **kwargs):
        super().__init__(message, code="PERMISSION_DENIED", **kwargs)


class NotFoundError(ERPMaxException):
    """Resource not found"""

    def __init__(self, resource: str, **kwargs):
        message = f"{resource} not found"
        super().__init__(message, code="NOT_FOUND", **kwargs)


class AlreadyExistsError(ERPMaxException):
    """Resource already exists"""

    def __init__(self, resource: str, **kwargs):
        message = f"{resource} already exists"
        super().__init__(message, code="ALREADY_EXISTS", **kwargs)


class ValidationError(ERPMaxException):
    """Validation error"""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        super().__init__(message, code="VALIDATION_ERROR", details=details, **kwargs)


class TenantError(ERPMaxException):
    """Tenant-related error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="TENANT_ERROR", **kwargs)


class SubscriptionError(ERPMaxException):
    """Subscription-related error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="SUBSCRIPTION_ERROR", **kwargs)


class ProvisioningError(ERPMaxException):
    """Provisioning-related error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="PROVISIONING_ERROR", **kwargs)


class PaymentError(ERPMaxException):
    """Payment-related error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="PAYMENT_ERROR", **kwargs)


# HTTP Exception helpers
def credentials_exception(
    detail: str = "Could not validate credentials",
) -> HTTPException:
    """Return 401 Unauthorized exception"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden_exception(detail: str = "Permission denied") -> HTTPException:
    """Return 403 Forbidden exception"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def not_found_exception(detail: str = "Resource not found") -> HTTPException:
    """Return 404 Not Found exception"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail,
    )


def conflict_exception(detail: str = "Resource already exists") -> HTTPException:
    """Return 409 Conflict exception"""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


def bad_request_exception(detail: str = "Bad request") -> HTTPException:
    """Return 400 Bad Request exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


def inactive_user_exception() -> HTTPException:
    """Return 400 Bad Request for inactive user"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Inactive user",
    )


def invalid_tenant_exception() -> HTTPException:
    """Return 403 Forbidden for invalid tenant access"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have access to this tenant",
    )


def subscription_required_exception() -> HTTPException:
    """Return 402 Payment Required for missing subscription"""
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail="Active subscription required",
    )
