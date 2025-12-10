from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, Field


T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration"""

    class Config:
        from_attributes = True
        populate_by_name = True


class PaginationInfo(BaseModel):
    """Pagination metadata"""

    total: int = Field(..., description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")


class ErrorInfo(BaseModel):
    """Error details"""

    code: Optional[str] = Field(None, description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")


class BaseResponse(BaseModel, Generic[T]):
    """Base response wrapper"""

    status: str = Field(..., description="Response status: 'success' or 'error'")
    data: Optional[T] = None
    error: Optional[ErrorInfo] = None

    class Config:
        json_schema_extra = {
            "example": {"status": "success", "data": {}, "error": None}
        }


class ListResponse(BaseResponse[List[T]], Generic[T]):
    """Response for list endpoints with pagination"""

    pagination: Optional[PaginationInfo] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": [],
                "pagination": {"total": 100, "page": 1, "size": 20, "pages": 5},
                "error": None,
            }
        }


class SingleResponse(BaseResponse[T], Generic[T]):
    """Response for single item endpoints"""

    pass


class MessageResponse(BaseModel):
    """Simple message response"""

    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
            }
        }
