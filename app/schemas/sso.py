"""SSO schemas"""

from datetime import datetime
from pydantic import BaseModel, Field


class SSOTokenResponse(BaseModel):
    """Response with SSO token and URL"""

    sso_url: str = Field(..., description="Full SSO URL with token")
    token: str = Field(..., description="One-time SSO token")
    expires_at: datetime = Field(..., description="Token expiration timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "sso_url": "https://tenant.erpnext.com/api/method/erpmax.sso.login?token=abc123xyz",
                "token": "abc123xyz",
                "expires_at": "2024-01-15T10:30:00Z",
            }
        }
    }


class SSOCallbackRequest(BaseModel):
    """SSO callback validation request"""

    token: str = Field(..., description="One-time SSO token")
    redirect: str | None = Field(None, description="Optional redirect path after login")

    model_config = {
        "json_schema_extra": {"example": {"token": "abc123xyz", "redirect": "/desk"}}
    }
