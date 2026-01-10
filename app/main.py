import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.api.v1 import api_router

logger = logging.getLogger(__name__)

settings = get_settings()

# Create FastAPI app
fastapi_app = FastAPI(
    title=settings.app_name,
    description="ERPMax SaaS Orchestrator API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "X-Content-Range"],
    max_age=600,  # Cache preflight requests for 10 minutes
)


# Exception handlers
@fastapi_app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed logging"""
    errors = exc.errors()

    logger.error(
        f"Validation error on {request.method} {request.url.path} - "
        f"Errors: {errors}"
    )

    # Format errors for better readability
    formatted_errors = []
    for error in errors:
        formatted_errors.append(
            {
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Validation error",
            "errors": formatted_errors,
        },
    )


# Include API routers
fastapi_app.include_router(api_router, prefix="/api/v1")

# Import Socket.IO event handlers and namespaces
from app.realtime import events  # noqa: E402, F401
from app.realtime.namespaces import notifications  # noqa: E402, F401
from app.realtime.namespaces import provisioning  # noqa: E402, F401
from app.realtime.namespaces import billing  # noqa: E402, F401

# Mount Socket.IO app
from app.realtime.server import socket_app

fastapi_app.mount("/ws", socket_app)

# Export as 'app' for compatibility
app = fastapi_app


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
