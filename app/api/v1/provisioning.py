"""Provisioning endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_current_active_user,
    get_current_tenant,
    require_role,
    Pagination,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.models import Tenant, User
from app.models.enums import TenantRole
from app.schemas.base import SingleResponse, ListResponse, MessageResponse
from app.schemas.provisioning import (
    CreateProvisioningJobRequest,
    ProvisioningJobResponse,
)
from app.services.provisioning import ProvisioningService


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/jobs",
    response_model=SingleResponse[ProvisioningJobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create provisioning job",
    description="Create provisioning job for current tenant (owner/admin only).",
    dependencies=[Depends(require_role(TenantRole.OWNER, TenantRole.ADMIN))],
)
async def create_job(
    data: CreateProvisioningJobRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = ProvisioningService(db)
        job = await service.create_job(
            tenant_id=current_tenant.id, job_type=data.job_type
        )
        return SingleResponse(
            status="success", data=ProvisioningJobResponse.model_validate(job)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Create provisioning job error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create provisioning job",
        )


@router.get(
    "/jobs",
    response_model=ListResponse[ProvisioningJobResponse],
    summary="List provisioning jobs",
    description="List provisioning jobs for current tenant.",
)
async def list_jobs(
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    pagination: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = ProvisioningService(db)
        jobs, total = await service.list_jobs(
            tenant_id=current_tenant.id,
            limit=pagination.limit,
            offset=pagination.skip,
        )
        data = [ProvisioningJobResponse.model_validate(j) for j in jobs]
        return ListResponse(
            status="success",
            data=data,
            pagination=pagination.get_pagination_info(total),
        )
    except Exception as e:
        logger.error(f"List provisioning jobs error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list provisioning jobs",
        )


@router.get(
    "/jobs/{job_id}",
    response_model=SingleResponse[ProvisioningJobResponse],
    summary="Get provisioning job",
    description="Get provisioning job by id (must belong to current tenant).",
)
async def get_job(
    job_id: UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = ProvisioningService(db)
        job = await service.get_job(job_id=job_id)
        if job.tenant_id != current_tenant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
            )

        return SingleResponse(
            status="success", data=ProvisioningJobResponse.model_validate(job)
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Get provisioning job error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get provisioning job",
        )


@router.post(
    "/jobs/{job_id}/retry",
    response_model=SingleResponse[ProvisioningJobResponse],
    summary="Retry provisioning job",
    description="Retry provisioning job (owner/admin only).",
    dependencies=[Depends(require_role(TenantRole.OWNER, TenantRole.ADMIN))],
)
async def retry_job(
    job_id: UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = ProvisioningService(db)
        job = await service.get_job(job_id=job_id)
        if job.tenant_id != current_tenant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
            )

        job = await service.retry_job(job_id=job_id)
        return SingleResponse(
            status="success", data=ProvisioningJobResponse.model_validate(job)
        )

    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Retry provisioning job error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry provisioning job",
        )


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=SingleResponse[ProvisioningJobResponse],
    summary="Cancel provisioning job",
    description="Cancel provisioning job (owner/admin only).",
    dependencies=[Depends(require_role(TenantRole.OWNER, TenantRole.ADMIN))],
)
async def cancel_job(
    job_id: UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = ProvisioningService(db)
        job = await service.get_job(job_id=job_id)
        if job.tenant_id != current_tenant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
            )

        job = await service.cancel_job(job_id=job_id)
        return SingleResponse(
            status="success", data=ProvisioningJobResponse.model_validate(job)
        )

    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Cancel provisioning job error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel provisioning job",
        )
