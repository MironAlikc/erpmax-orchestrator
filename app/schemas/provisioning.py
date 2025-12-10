from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import Field

from app.schemas.base import BaseSchema
from app.models.enums import JobStatus, JobType


class ProvisioningJobResponse(BaseSchema):
    """Schema for provisioning job response"""

    id: UUID = Field(..., description="Job unique identifier")
    tenant_id: UUID = Field(..., description="Tenant ID")
    status: JobStatus = Field(..., description="Job status")
    job_type: JobType = Field(..., description="Job type")
    progress: int = Field(..., ge=0, le=100, description="Job progress percentage")
    message: Optional[str] = Field(None, description="Current status message")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(
        None, description="Job completion timestamp"
    )
    created_at: datetime = Field(..., description="Job creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "status": "running",
                "job_type": "create_site",
                "progress": 45,
                "message": "Creating database...",
                "error": None,
                "started_at": "2024-01-01T00:00:00Z",
                "completed_at": None,
                "created_at": "2024-01-01T00:00:00Z",
            }
        }


class CreateProvisioningJobRequest(BaseSchema):
    """Schema for creating provisioning job"""

    job_type: JobType = Field(..., description="Type of provisioning job")

    class Config:
        json_schema_extra = {"example": {"job_type": "create_site"}}
