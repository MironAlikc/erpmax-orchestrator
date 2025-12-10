"""API v1 router"""

from fastapi import APIRouter

from app.api.v1 import auth, tenants

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])

# Future routers will be added here:
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
# api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
# api_router.include_router(provisioning.router, prefix="/provisioning", tags=["Provisioning"])
