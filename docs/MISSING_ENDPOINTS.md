# Відсутні ендпоінти в Flutter документації

## Огляд

Цей документ містить ендпоінти, які присутні в API, але не були включені до основної документації Flutter (`flutter_implementation.md`).

---

## SSO - Validate Token (Helper Endpoint)

### Ендпоінт

```http
GET /api/v1/sso/erpnext/validate/{token}
```

### Опис

Валідація SSO токена без його споживання. Це допоміжний ендпоінт для перевірки валідності токена без видалення його з Redis.

**Важливо:** Цей ендпоінт НЕ споживає токен. Використовуйте `/sso/erpnext/callback` для фактичного SSO потоку.

### Параметри

**Path Parameters:**

- `token` (string, required) - SSO токен для валідації

### Response

**Success (200):**

```json
{
  "valid": true,
  "user_id": "uuid",
  "tenant_id": "uuid",
  "created_at": "2024-12-23T12:00:00"
}
```

**Error (404):**

```json
{
  "detail": "Token not found or expired"
}
```

---

## Flutter Implementation

### Додати до api_endpoints.dart

```dart
class ApiEndpoints {
  // ... existing endpoints ...
  
  // SSO
  static const String ssoToken = '/sso/erpnext/token';
  static const String ssoCallback = '/sso/erpnext/callback';
  static String ssoValidate(String token) => '/sso/erpnext/validate/$token';  // NEW
}
```

### Додати до sso_service.dart

```dart
class SSOService {
  final ApiClient _client;
  
  SSOService({required ApiClient client}) : _client = client;
  
  /// Generate SSO token for ERPNext login
  Future<SSOTokenResponse> generateToken() async {
    final response = await _client.post(ApiEndpoints.ssoToken);
    return SSOTokenResponse.fromJson(response.data['data']);
  }
  
  /// Validate SSO token without consuming it (NEW)
  Future<SSOTokenValidation> validateToken(String token) async {
    final response = await _client.get(ApiEndpoints.ssoValidate(token));
    return SSOTokenValidation.fromJson(response.data);
  }
}

// Response model for token validation
class SSOTokenValidation {
  final bool valid;
  final String userId;
  final String tenantId;
  final DateTime createdAt;
  
  SSOTokenValidation({
    required this.valid,
    required this.userId,
    required this.tenantId,
    required this.createdAt,
  });
  
  factory SSOTokenValidation.fromJson(Map<String, dynamic> json) {
    return SSOTokenValidation(
      valid: json['valid'],
      userId: json['user_id'],
      tenantId: json['tenant_id'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
```

### Приклад використання

```dart
// Validate token before using it
final ssoService = SSOService(client: apiClient);

try {
  final validation = await ssoService.validateToken('your-token-here');
  
  if (validation.valid) {
    dev.log('Token is valid for user: ${validation.userId}');
    // Proceed with SSO flow
  } else {
    dev.log('Token is invalid');
  }
} catch (e) {
  dev.log('Token validation failed: $e');
}
```

---

## Примітки

1. **Використання:** Цей ендпоінт корисний для debug/testing цілей, але не є обов'язковим для основного SSO потоку.

2. **Безпека:** Токен залишається в Redis після валідації, тому цей ендпоінт не повинен використовуватися для фактичної автентифікації.

3. **TTL:** Токен має TTL 60 секунд і автоматично видаляється після використання через `/sso/erpnext/callback`.

---

**Дата створення:** 23 грудня 2024  
**Версія API:** v1
