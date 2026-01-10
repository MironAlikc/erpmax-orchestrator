# Test Users

This document describes test users available for development and testing.

## Creating Test Users

Run the script to create test users:

```bash
python scripts/create_test_users.py
```

This will create two users with their tenants and subscriptions.

## Available Test Accounts

### Regular User

- **Email:** `test@example.com`
- **Password:** `password`
- **Company:** Test Company
- **Role:** Owner
- **Superuser:** No

### Admin User

- **Email:** `admin@example.com`
- **Password:** `admin123`
- **Company:** Admin Company
- **Role:** Owner
- **Superuser:** Yes

## Login Example

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password"
  }'
```

## Notes

- The script will delete existing test users before creating new ones
- Each user has their own tenant with a trial/active subscription
- Both users have Owner role in their respective tenants
- The admin user has superuser privileges for system-wide operations
