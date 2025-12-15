from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1 import api_router

settings = get_settings()

# Create FastAPI app
fastapi_app = FastAPI(
    title=settings.app_name,
    description="ERPMax SaaS Orchestrator API",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
