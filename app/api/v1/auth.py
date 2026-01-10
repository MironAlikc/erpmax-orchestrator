"""Authentication endpoints"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user
from app.core.exceptions import (
    AuthenticationError,
    AlreadyExistsError,
    NotFoundError,
)
from app.models import User
from app.services.auth import AuthService
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    Token,
    SwitchTenantRequest,
    SwitchTenantResponse,
)
from app.schemas.base import SingleResponse, MessageResponse
from app.schemas.user import UserResponse, UserWithTenants

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/register",
    response_model=SingleResponse[RegisterResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Register new user with company. Creates user, tenant, and trial subscription.",
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register new user:
    - Creates User account
    - Creates Tenant (from company_name)
    - Assigns user as Owner
    - Creates Trial subscription (14 days)
    - Returns JWT tokens
    """
    try:
        auth_service = AuthService(db)
        user, tenant, tokens = await auth_service.register(data)

        # Get user's tenants info
        tenants_data = await auth_service._get_user_tenants(user.id)

        response_data = RegisterResponse(
            **tokens,
            user=UserResponse.model_validate(user),
            tenants=tenants_data,
            current_tenant=tenant,
        )

        logger.info(f"User registered: {user.email}, tenant: {tenant.name}")

        return SingleResponse(
            status="success",
            data=response_data,
        )

    except AlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.message),
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@router.post(
    "/login",
    response_model=SingleResponse[LoginResponse],
    summary="Login user",
    description="Authenticate user and return JWT tokens with user info and tenants.",
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login user:
    - Validates credentials
    - Returns JWT tokens
    - Returns user info with all tenants
    - Returns current/default tenant
    """
    try:
        auth_service = AuthService(db)
        user, tenants_data, current_tenant, tokens = await auth_service.login(data)

        response_data = LoginResponse(
            **tokens,
            user=UserResponse.model_validate(user),
            tenants=tenants_data,
            current_tenant=current_tenant,
        )

        logger.info(f"User logged in: {user.email}")

        return SingleResponse(
            status="success",
            data=response_data,
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e.message),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.post(
    "/refresh",
    response_model=SingleResponse[Token],
    summary="Refresh access token",
    description="Get new access token using refresh token.",
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh tokens:
    - Validates refresh token
    - Returns new access and refresh tokens
    """
    try:
        auth_service = AuthService(db)
        tokens = await auth_service.refresh_tokens(data.refresh_token)

        response_data = Token(**tokens)

        return SingleResponse(
            status="success",
            data=response_data,
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e.message),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Logout user (currently just returns success, token blacklist will be added later).",
)
async def logout(
    current_user: User = Depends(get_current_active_user),
):
    """
    Logout user:
    - Currently just returns success
    - TODO: Add token to Redis blacklist
    """
    logger.info(f"User logged out: {current_user.email}")

    return MessageResponse(
        status="success",
        message="Logged out successfully",
    )


@router.get(
    "/me",
    response_model=SingleResponse[UserWithTenants],
    summary="Get current user info",
    description="Get current authenticated user with tenants.",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user:
    - Returns user info
    - Returns all user's tenants with roles
    - Returns current/default tenant
    """
    try:
        auth_service = AuthService(db)
        user, tenants_data, current_tenant = await auth_service.get_current_user_info(
            current_user.id
        )

        # Create response with tenants
        user_dict = UserResponse.model_validate(user).model_dump()
        user_dict["tenants"] = tenants_data

        response_data = UserWithTenants(**user_dict)

        return SingleResponse(
            status="success",
            data=response_data,
        )

    except Exception as e:
        logger.error(f"Get user info error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user info",
        )


@router.post(
    "/switch-tenant",
    response_model=SingleResponse[SwitchTenantResponse],
    summary="Switch current tenant",
    description="Switch user's current tenant and get new tokens.",
)
async def switch_tenant(
    data: SwitchTenantRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Switch tenant:
    - Validates user has access to tenant
    - Updates default tenant
    - Returns new JWT tokens with new tenant_id
    """
    try:
        auth_service = AuthService(db)
        tenant, tokens = await auth_service.switch_tenant(
            current_user.id,
            data.tenant_id,
        )

        response_data = SwitchTenantResponse(
            **tokens,
            tenant=tenant,
        )

        logger.info(f"User {current_user.email} switched to tenant: {tenant.name}")

        return SingleResponse(
            status="success",
            data=response_data,
        )

    except (AuthenticationError, NotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e.message),
        )
    except Exception as e:
        logger.error(f"Switch tenant error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to switch tenant",
        )


# TODO: Phase 2 endpoints
# @router.post("/forgot-password")
# @router.post("/reset-password")
