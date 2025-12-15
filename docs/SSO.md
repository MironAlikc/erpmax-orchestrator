# SSO Service & API

## Purpose

SSO (Single Sign-On) enables seamless authentication between ERPMax Orchestrator and ERPNext instances.

- Generate one-time SSO tokens for ERPNext login
- Validate tokens and provide user session data
- Automatic token expiration (60 seconds)
- One-time use tokens stored in Redis

---

## Components

### Service

- `app/services/sso.py`
- `SSOService`

Responsibilities:

- generate one-time SSO token
- validate and consume token
- retrieve user session data for ERPNext

### API router

- `app/api/v1/sso.py`
- Mounted under `/api/v1/sso`

### Redis storage

- `app/core/redis.py`
- Tokens stored with 60-second TTL
- Automatic cleanup on expiration

---

## Data flow

1. **User requests SSO token**
   - Frontend calls `POST /api/v1/sso/erpnext/token`
   - Service generates secure random token
   - Token stored in Redis with user_id and tenant_id
   - Returns SSO URL with embedded token

2. **User clicks SSO URL**
   - Browser navigates to ERPNext with token parameter
   - ERPNext calls `GET /api/v1/sso/erpnext/callback?token=xxx`
   - Service validates token (one-time use)
   - Returns user and tenant data
   - ERPNext creates session and redirects user

3. **Token expiration**
   - Tokens expire after 60 seconds
   - Tokens deleted after first use
   - Invalid/expired tokens return 403 error

---

## API Endpoints

### Generate SSO token

- `POST /api/v1/sso/erpnext/token`
- Access: authenticated user with tenant access

Response:

```json
{
  "data": {
    "sso_url": "https://tenant.erpnext.com/api/method/erpmax.sso.login?token=abc123xyz",
    "token": "abc123xyz",
    "expires_at": "2024-01-15T10:30:00Z"
  }
}
```

### Validate SSO token (callback)

- `GET /api/v1/sso/erpnext/callback`
- Query params: `token` (required), `redirect` (optional, default: `/desk`)
- Access: public (called by ERPNext)

Response (success):

```json
{
  "success": true,
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "User Name"
    },
    "tenant": {
      "id": "uuid",
      "name": "Company Name",
      "slug": "company-slug"
    }
  },
  "redirect": "/desk"
}
```

Response (error):

```json
{
  "success": false,
  "error": "Invalid or expired SSO token",
  "redirect": "/login"
}
```

### Validate token (helper)

- `GET /api/v1/sso/erpnext/validate/{token}`
- Access: public
- Returns token info without consuming it

**Note**: This endpoint does NOT consume the token. Use `/callback` for actual SSO flow.

---

## Configuration

### Environment variables

Redis connection (already configured):

- `REDIS_HOST` (default: `localhost`)
- `REDIS_PORT` (default: `6379`)
- `REDIS_PASSWORD`

### Token settings

Configured in `SSOService`:

- `SSO_TOKEN_TTL`: 60 seconds
- `SSO_TOKEN_PREFIX`: `sso:token:`

---

## Security considerations

1. **One-time use**: Tokens are deleted after validation
2. **Short TTL**: 60-second expiration window
3. **Secure random**: Uses `secrets.token_urlsafe(32)`
4. **HTTPS required**: SSO URLs should use HTTPS in production
5. **Tenant validation**: Checks ERPNext site is provisioned

---

## ERPNext integration

ERPNext must implement the following:

1. **SSO endpoint**: `/api/method/erpmax.sso.login`
   - Receives token as query parameter
   - Calls Orchestrator callback endpoint
   - Creates user session based on response
   - Redirects to specified path

2. **Example ERPNext implementation**:

```python
@frappe.whitelist(allow_guest=True)
def sso_login(token, redirect="/desk"):
    """Handle SSO login from ERPMax Orchestrator"""
    import requests
    
    # Call Orchestrator callback
    response = requests.get(
        f"https://orchestrator.erpmax.com/api/v1/sso/erpnext/callback",
        params={"token": token, "redirect": redirect}
    )
    
    data = response.json()
    
    if not data.get("success"):
        frappe.throw(data.get("error", "SSO authentication failed"))
    
    # Create/update user session
    user_data = data["data"]["user"]
    tenant_data = data["data"]["tenant"]
    
    # Login user (implementation depends on ERPNext version)
    frappe.local.login_manager.login_as(user_data["email"])
    
    # Redirect to specified path
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = data.get("redirect", "/desk")
```

---

## Testing

Smoke tests: `tests/test_sso_api.py`

Run tests:

```bash
python -m pytest tests/test_sso_api.py -v
```

Tests cover:

- Token generation
- Token validation
- Session data retrieval
- Invalid token handling

---

## Local verification

1. Start Redis:

```bash
docker-compose up -d redis
```

1. Run API:

```bash
uvicorn app.main:app --reload
```

1. Generate SSO token via Swagger:
   - `http://127.0.0.1:8000/docs`
   - `POST /api/v1/sso/erpnext/token`

1. Copy SSO URL and test in browser (will fail without ERPNext)

---

## Limitations / Next steps

- ERPNext integration must be implemented separately
- Add rate limiting for token generation
- Add audit logging for SSO events
- Consider adding IP whitelisting for callback endpoint
- Add support for multiple ERPNext instances per tenant
