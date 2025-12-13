"""API v1 router"""

from fastapi import APIRouter

from app.api.v1 import auth, tenants, billing, provisioning

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(
    provisioning.router, prefix="/provisioning", tags=["Provisioning"]
)

# Future routers will be added here:
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
