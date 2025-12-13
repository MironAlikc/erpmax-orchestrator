"""Provisioning service - business logic for ERPNext site provisioning jobs"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.rabbitmq import publish_json
from app.models import ProvisioningJob
from app.models.enums import JobStatus, JobType


class ProvisioningService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._settings = get_settings()

    async def create_job(
        self, *, tenant_id: UUID, job_type: JobType
    ) -> ProvisioningJob:
        job = ProvisioningJob(
            tenant_id=tenant_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            progress=0,
            message="Queued",
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        await publish_json(
            queue_name=self._settings.provisioning_queue_name,
            message={"job_id": str(job.id)},
        )

        return job

    async def get_job(self, *, job_id: UUID) -> ProvisioningJob:
        result = await self.db.execute(
            select(ProvisioningJob).where(ProvisioningJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError("ProvisioningJob")
        return job

    async def list_jobs(
        self,
        *,
        tenant_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProvisioningJob], int]:
        total_result = await self.db.execute(
            select(func.count(ProvisioningJob.id)).where(
                ProvisioningJob.tenant_id == tenant_id
            )
        )
        total = int(total_result.scalar_one())

        result = await self.db.execute(
            select(ProvisioningJob)
            .where(ProvisioningJob.tenant_id == tenant_id)
            .order_by(ProvisioningJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        jobs = list(result.scalars().all())
        return jobs, total

    async def retry_job(self, *, job_id: UUID) -> ProvisioningJob:
        job = await self.get_job(job_id=job_id)

        if job.status not in {JobStatus.FAILED, JobStatus.COMPLETED}:
            raise ValidationError("Only failed/completed jobs can be retried")

        job.status = JobStatus.PENDING
        job.progress = 0
        job.message = "Queued"
        job.error = None
        job.started_at = None
        job.completed_at = None

        await self.db.commit()
        await self.db.refresh(job)

        await publish_json(
            queue_name=self._settings.provisioning_queue_name,
            message={"job_id": str(job.id)},
        )

        return job

    async def cancel_job(self, *, job_id: UUID) -> ProvisioningJob:
        job = await self.get_job(job_id=job_id)

        if job.status in {JobStatus.COMPLETED, JobStatus.FAILED}:
            return job

        job.status = JobStatus.FAILED
        job.error = "Cancelled by user"
        job.message = "Cancelled"
        job.progress = 0

        await self.db.commit()
        await self.db.refresh(job)

        return job
