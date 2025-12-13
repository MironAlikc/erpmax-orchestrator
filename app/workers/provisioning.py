from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import aio_pika

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models import ProvisioningJob, Tenant
from app.models.enums import JobStatus, JobType, TenantStatus


logger = logging.getLogger(__name__)


async def _process_job(*, job_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        job = await db.get(ProvisioningJob, job_id)
        if not job:
            logger.warning("Provisioning job not found: %s", job_id)
            return

        if job.status not in {JobStatus.PENDING, JobStatus.FAILED}:
            logger.info("Skipping job %s with status %s", job.id, job.status)
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.progress = 10
        job.message = "Started"
        job.error = None

        tenant = await db.get(Tenant, job.tenant_id)
        if tenant and job.job_type == JobType.CREATE_SITE:
            tenant.status = TenantStatus.PROVISIONING

        await db.commit()

        try:
            await asyncio.sleep(0.1)

            job.progress = 70
            job.message = "Processing"
            await db.commit()

            await asyncio.sleep(0.1)

            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.completed_at = datetime.utcnow()
            job.message = "Completed"

            if tenant and job.job_type == JobType.CREATE_SITE:
                tenant.status = TenantStatus.ACTIVE

            await db.commit()
            logger.info("Provisioning job completed: %s", job.id)

        except Exception as e:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error = str(e)
            job.message = "Failed"
            await db.commit()
            logger.exception("Provisioning job failed: %s", job.id)


async def _handle_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process(requeue=False):
        try:
            payload = json.loads(message.body.decode("utf-8"))
        except Exception:
            logger.warning("Invalid message payload")
            return

        job_id_str = (payload or {}).get("job_id")
        if not job_id_str:
            logger.warning("Message missing job_id")
            return

        try:
            job_id = UUID(job_id_str)
        except Exception:
            logger.warning("Invalid job_id: %s", job_id_str)
            return

        await _process_job(job_id=job_id)


async def main() -> None:
    settings = get_settings()

    rabbitmq_url = settings.rabbitmq_url
    if not rabbitmq_url:
        rabbitmq_url = (
            f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}"
            f"@{settings.rabbitmq_host}:{settings.rabbitmq_port}/"
        )

    queue_name = settings.provisioning_queue_name

    connection = await aio_pika.connect_robust(rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        queue = await channel.declare_queue(queue_name, durable=True)

        logger.info("Worker started. Queue=%s", queue_name)
        await queue.consume(_handle_message)

        await asyncio.Future()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
