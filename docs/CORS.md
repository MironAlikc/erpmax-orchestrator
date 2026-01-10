# CORS Configuration

## Overview

Cross-Origin Resource Sharing (CORS) is configured to allow frontend applications to communicate with the API from different origins.

## Configuration

CORS settings are managed through environment variables and can be customized per environment.

### Environment Variable

```bash
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000
```

### Supported Formats

1. **Comma-separated list** (recommended):

   ```bash
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
   ```

2. **Wildcard** (development only, NOT recommended for production):

   ```bash
   ALLOWED_ORIGINS=*
   ```

## Default Settings

The application includes the following CORS middleware configuration:

- **Allowed Origins**: Configured via `ALLOWED_ORIGINS` environment variable
- **Allow Credentials**: `true` (enables cookies and authorization headers)
- **Allowed Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`
- **Allowed Headers**: All headers (`*`)
- **Exposed Headers**: `Content-Range`, `X-Content-Range`
- **Max Age**: 600 seconds (preflight cache duration)

## Environment-Specific Configuration

### Development

```bash
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000
```

### Staging

```bash
ALLOWED_ORIGINS=https://staging.erpmax.com,https://staging-admin.erpmax.com
```

### Production

```bash
ALLOWED_ORIGINS=https://app.erpmax.com,https://admin.erpmax.com
```

## Security Considerations

1. **Never use wildcard (`*`) in production** - it allows any website to make requests to your API
2. **Always specify exact origins** - include protocol (http/https), domain, and port
3. **Use HTTPS in production** - ensure all production origins use `https://`
4. **Limit origins** - only add origins that need access to the API

## Testing CORS

### Using curl

```bash
# Test preflight request
curl -X OPTIONS http://localhost:8000/api/v1/auth/login \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v

# Test actual request
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}' \
  -v
```

### Expected Headers

Successful CORS response should include:

```http
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: *
```

## Troubleshooting

### Issue: CORS error in browser

**Symptoms**: Browser console shows CORS policy error

**Solutions**:

1. Verify the origin is in `ALLOWED_ORIGINS`
2. Check protocol matches (http vs https)
3. Verify port number is included if non-standard
4. Restart the server after changing `.env`

### Issue: Credentials not working

**Symptoms**: Cookies or Authorization headers not sent

**Solutions**:

1. Ensure `allow_credentials=True` in middleware
2. Frontend must set `credentials: 'include'` in fetch/axios
3. Cannot use wildcard (`*`) with credentials

### Issue: Custom headers blocked

**Symptoms**: Custom headers not received by API

**Solutions**:

1. Verify headers are in `Access-Control-Allow-Headers`
2. Check preflight request is successful
3. Ensure header names match exactly (case-insensitive)

## Code Reference

- Configuration: `app/core/config.py`
- Middleware setup: `app/main.py`
- Environment template: `.env.example`
