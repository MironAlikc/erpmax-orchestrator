"""Tenant endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_current_active_user,
    get_current_tenant,
    require_role,
    Pagination,
)
from app.core.exceptions import (
    NotFoundError,
    AuthorizationError,
    AlreadyExistsError,
    ValidationError,
)
from app.models import User, Tenant
from app.models.enums import TenantRole
from app.services.tenant import TenantService
from app.schemas.tenant import (
    TenantResponse,
    TenantUpdate,
    TenantUserResponse,
    TenantInviteRequest,
    TenantUserUpdateRole,
)
from app.schemas.base import SingleResponse, ListResponse, MessageResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=ListResponse[TenantResponse],
    summary="List user's tenants",
    description="Get all tenants that the current user has access to.",
)
async def list_tenants(
    current_user: User = Depends(get_current_active_user),
    pagination: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    List all tenants for current user:
    - Returns tenants with pagination
    - Includes user's role in each tenant
    """
    try:
        tenant_service = TenantService(db)
        tenants, total = await tenant_service.get_user_tenants(
            current_user.id,
            page=pagination.page,
            size=pagination.size,
        )

        tenants_data = [TenantResponse.model_validate(t) for t in tenants]

        return ListResponse(
            status="success",
            data=tenants_data,
            pagination=pagination.get_pagination_info(total),
        )

    except Exception as e:
        logger.error(f"List tenants error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tenants",
        )


@router.get(
    "/current",
    response_model=SingleResponse[TenantResponse],
    summary="Get current tenant",
    description="Get current tenant details with subscription info.",
)
async def get_current_tenant_info(
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current tenant:
    - Returns tenant details
    - Includes subscription info
    - Includes limits from plan
    """
    try:
        tenant_service = TenantService(db)
        tenant = await tenant_service.get_current_tenant(
            current_tenant.id,
            current_user.id,
        )

        tenant_data = TenantResponse.model_validate(tenant)

        return SingleResponse(
            status="success",
            data=tenant_data,
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.message),
        )
    except Exception as e:
        logger.error(f"Get current tenant error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tenant",
        )


@router.get(
    "/{tenant_id}",
    response_model=SingleResponse[TenantResponse],
    summary="Get tenant by ID",
    description="Get specific tenant details (requires access).",
)
async def get_tenant(
    tenant_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get tenant by ID:
    - Requires user to have access to tenant
    - Returns tenant details
    """
    try:
        tenant_service = TenantService(db)
        tenant = await tenant_service.get_tenant_by_id(
            tenant_id,
            current_user.id,
        )

        tenant_data = TenantResponse.model_validate(tenant)

        return SingleResponse(
            status="success",
            data=tenant_data,
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.message),
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e.message),
        )
    except Exception as e:
        logger.error(f"Get tenant error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tenant",
        )


@router.patch(
    "/{tenant_id}",
    response_model=SingleResponse[TenantResponse],
    summary="Update tenant",
    description="Update tenant details (owner/admin only).",
    dependencies=[Depends(require_role(TenantRole.OWNER, TenantRole.ADMIN))],
)
async def update_tenant(
    tenant_id: UUID,
    data: TenantUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update tenant:
    - Requires owner or admin role
    - Can update name and settings
    """
    try:
        tenant_service = TenantService(db)
        tenant = await tenant_service.update_tenant(
            tenant_id,
            current_user.id,
            data,
        )

        tenant_data = TenantResponse.model_validate(tenant)

        logger.info(f"Tenant {tenant_id} updated by {current_user.email}")

        return SingleResponse(
            status="success",
            data=tenant_data,
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.message),
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e.message),
        )
    except Exception as e:
        logger.error(f"Update tenant error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tenant",
        )


@router.get(
    "/{tenant_id}/users",
    response_model=ListResponse[TenantUserResponse],
    summary="List tenant users",
    description="Get all users in tenant (owner/admin only).",
    dependencies=[Depends(require_role(TenantRole.OWNER, TenantRole.ADMIN))],
)
async def list_tenant_users(
    tenant_id: UUID,
    current_user: User = Depends(get_current_active_user),
    pagination: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    List tenant users:
    - Requires owner or admin role
    - Returns users with roles
    - Includes pagination
    """
    try:
        tenant_service = TenantService(db)
        users_data, total = await tenant_service.get_tenant_users(
            tenant_id,
            current_user.id,
            page=pagination.page,
            size=pagination.size,
        )

        users_response = [TenantUserResponse(**u) for u in users_data]

        return ListResponse(
            status="success",
            data=users_response,
            pagination=pagination.get_pagination_info(total),
        )

    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e.message),
        )
    except Exception as e:
        logger.error(f"List tenant users error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users",
        )


@router.post(
    "/{tenant_id}/users/invite",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite user to tenant",
    description="Invite user by email (owner/admin only).",
    dependencies=[Depends(require_role(TenantRole.OWNER, TenantRole.ADMIN))],
)
async def invite_user(
    tenant_id: UUID,
    data: TenantInviteRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Invite user to tenant:
    - Requires owner or admin role
    - User must exist in system
    - Sends invitation email (TODO)
    """
    try:
        tenant_service = TenantService(db)
        result = await tenant_service.invite_user(
            tenant_id,
            current_user.id,
            data.email,
            data.role,
        )

        logger.info(
            f"User {data.email} invited to tenant {tenant_id} by {current_user.email}"
        )

        return MessageResponse(
            status="success",
            message=result["message"],
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.message),
        )
    except AlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.message),
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e.message),
        )
    except Exception as e:
        logger.error(f"Invite user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invite user",
        )


@router.patch(
    "/{tenant_id}/users/{user_id}",
    response_model=MessageResponse,
    summary="Update user role",
    description="Update user's role in tenant (owner only).",
    dependencies=[Depends(require_role(TenantRole.OWNER))],
)
async def update_user_role(
    tenant_id: UUID,
    user_id: UUID,
    data: TenantUserUpdateRole,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user role:
    - Requires owner role
    - Cannot change owner role
    """
    try:
        tenant_service = TenantService(db)
        result = await tenant_service.update_user_role(
            tenant_id,
            current_user.id,
            user_id,
            data.role,
        )

        logger.info(
            f"User {user_id} role updated in tenant {tenant_id} by {current_user.email}"
        )

        return MessageResponse(
            status="success",
            message=result["message"],
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.message),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.message),
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e.message),
        )
    except Exception as e:
        logger.error(f"Update user role error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role",
        )


@router.delete(
    "/{tenant_id}/users/{user_id}",
    response_model=MessageResponse,
    summary="Remove user from tenant",
    description="Remove user from tenant (owner/admin only).",
    dependencies=[Depends(require_role(TenantRole.OWNER, TenantRole.ADMIN))],
)
async def remove_user(
    tenant_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove user from tenant:
    - Requires owner or admin role
    - Cannot remove owner
    - Cannot remove yourself
    """
    try:
        tenant_service = TenantService(db)
        result = await tenant_service.remove_user(
            tenant_id,
            current_user.id,
            user_id,
        )

        logger.info(
            f"User {user_id} removed from tenant {tenant_id} by {current_user.email}"
        )

        return MessageResponse(
            status="success",
            message=result["message"],
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.message),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.message),
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e.message),
        )
    except Exception as e:
        logger.error(f"Remove user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove user",
        )
