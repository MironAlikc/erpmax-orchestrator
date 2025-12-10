# Base schemas
from app.schemas.base import (
    BaseSchema,
    PaginationInfo,
    ErrorInfo,
    BaseResponse,
    ListResponse,
    SingleResponse,
    MessageResponse,
)

# User schemas
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserWithTenants,
)

# Tenant schemas
from app.schemas.tenant import (
    TenantBase,
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantWithSubscription,
    TenantUserResponse,
    TenantInviteRequest,
    TenantUserUpdateRole,
)

# Auth schemas
from app.schemas.auth import (
    Token,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    RefreshTokenRequest,
    SwitchTenantRequest,
    SwitchTenantResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

# Plan schemas
from app.schemas.plan import PlanResponse

# Subscription schemas
from app.schemas.subscription import (
    SubscriptionResponse,
    SubscriptionWithPlan,
    CheckoutRequest,
    CheckoutResponse,
    CancelSubscriptionRequest,
    PaymentEventResponse,
)

# Provisioning schemas
from app.schemas.provisioning import (
    ProvisioningJobResponse,
    CreateProvisioningJobRequest,
)

__all__ = [
    # Base
    "BaseSchema",
    "PaginationInfo",
    "ErrorInfo",
    "BaseResponse",
    "ListResponse",
    "SingleResponse",
    "MessageResponse",
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserWithTenants",
    # Tenant
    "TenantBase",
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    "TenantWithSubscription",
    "TenantUserResponse",
    "TenantInviteRequest",
    "TenantUserUpdateRole",
    # Auth
    "Token",
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RegisterResponse",
    "RefreshTokenRequest",
    "SwitchTenantRequest",
    "SwitchTenantResponse",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    # Plan
    "PlanResponse",
    # Subscription
    "SubscriptionResponse",
    "SubscriptionWithPlan",
    "CheckoutRequest",
    "CheckoutResponse",
    "CancelSubscriptionRequest",
    "PaymentEventResponse",
    # Provisioning
    "ProvisioningJobResponse",
    "CreateProvisioningJobRequest",
]
