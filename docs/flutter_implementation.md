# Flutter API Implementation Guide

## Огляд

Цей документ описує імплементацію клієнтської частини для Flutter додатку, що взаємодіє з ERPMax Orchestrator API.

**Base URL:** `https://api.erpmax.com` (production) або `http://localhost:8000` (development)

**API Version:** v1

**Prefix:** `/api/v1`

---

## Архітектура клієнта

### Рекомендована структура

```
lib/
├── core/
│   ├── api/
│   │   ├── api_client.dart          # HTTP client wrapper
│   │   ├── api_endpoints.dart       # Endpoints constants
│   │   └── api_interceptor.dart     # JWT interceptor
│   ├── models/
│   │   ├── user.dart
│   │   ├── tenant.dart
│   │   ├── subscription.dart
│   │   ├── plan.dart
│   │   └── provisioning_job.dart
│   └── services/
│       ├── auth_service.dart
│       ├── tenant_service.dart
│       ├── billing_service.dart
│       ├── provisioning_service.dart
│       ├── sso_service.dart
│       └── realtime_service.dart
├── features/
│   ├── auth/
│   ├── dashboard/
│   ├── billing/
│   └── settings/
└── main.dart
```

---

## Залежності (pubspec.yaml)

```yaml
dependencies:
  flutter:
    sdk: flutter
  
  # HTTP client
  dio: ^5.4.0
  
  # State management
  flutter_riverpod: ^2.4.9
  
  # Local storage
  flutter_secure_storage: ^9.0.0
  shared_preferences: ^2.2.2
  
  # Real-time communication
  socket_io_client: ^2.0.3
  
  # JSON serialization
  json_annotation: ^4.8.1
  freezed_annotation: ^2.4.1
  
  # Code generation
  build_runner: ^2.4.7
  json_serializable: ^6.7.1
  freezed: ^2.4.6
```

---

## 1. API Client Setup

### api_client.dart

```dart
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:developer' as dev;

class ApiClient {
  static const String baseUrl = 'http://localhost:8000/api/v1';
  
  final Dio _dio;
  final FlutterSecureStorage _storage;
  
  ApiClient({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage(),
        _dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 30),
          receiveTimeout: const Duration(seconds: 30),
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
        )) {
    _setupInterceptors();
  }
  
  void _setupInterceptors() {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          // Add JWT token to headers
          final token = await _storage.read(key: 'access_token');
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          
          dev.log('Request: ${options.method} ${options.path}');
          return handler.next(options);
        },
        onResponse: (response, handler) {
          dev.log('Response: ${response.statusCode} ${response.requestOptions.path}');
          return handler.next(response);
        },
        onError: (error, handler) async {
          dev.log('Error: ${error.response?.statusCode} ${error.message}');
          
          // Handle 401 - refresh token
          if (error.response?.statusCode == 401) {
            try {
              await _refreshToken();
              // Retry original request
              return handler.resolve(await _retry(error.requestOptions));
            } catch (e) {
              // Refresh failed - logout
              await _storage.deleteAll();
              return handler.reject(error);
            }
          }
          
          return handler.next(error);
        },
      ),
    );
  }
  
  Future<void> _refreshToken() async {
    final refreshToken = await _storage.read(key: 'refresh_token');
    if (refreshToken == null) throw Exception('No refresh token');
    
    final response = await _dio.post('/auth/refresh', data: {
      'refresh_token': refreshToken,
    });
    
    final data = response.data['data'];
    await _storage.write(key: 'access_token', value: data['access_token']);
    await _storage.write(key: 'refresh_token', value: data['refresh_token']);
  }
  
  Future<Response<dynamic>> _retry(RequestOptions requestOptions) async {
    final options = Options(
      method: requestOptions.method,
      headers: requestOptions.headers,
    );
    
    return _dio.request<dynamic>(
      requestOptions.path,
      data: requestOptions.data,
      queryParameters: requestOptions.queryParameters,
      options: options,
    );
  }
  
  // HTTP methods
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    return _dio.get<T>(path, queryParameters: queryParameters);
  }
  
  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    return _dio.post<T>(path, data: data, queryParameters: queryParameters);
  }
  
  Future<Response<T>> patch<T>(
    String path, {
    dynamic data,
  }) async {
    return _dio.patch<T>(path, data: data);
  }
  
  Future<Response<T>> delete<T>(String path) async {
    return _dio.delete<T>(path);
  }
}
```

### api_endpoints.dart

```dart
class ApiEndpoints {
  // Auth
  static const String register = '/auth/register';
  static const String login = '/auth/login';
  static const String refresh = '/auth/refresh';
  static const String logout = '/auth/logout';
  static const String me = '/auth/me';
  static const String switchTenant = '/auth/switch-tenant';
  
  // Tenants
  static const String tenants = '/tenants';
  static const String currentTenant = '/tenants/current';
  static String tenantById(String id) => '/tenants/$id';
  static String tenantUsers(String id) => '/tenants/$id/users';
  static String inviteUser(String id) => '/tenants/$id/users/invite';
  static String updateUserRole(String tenantId, String userId) =>
      '/tenants/$tenantId/users/$userId';
  
  // Billing
  static const String plans = '/billing/plans';
  static const String subscription = '/billing/subscription';
  static const String checkout = '/billing/checkout';
  static const String cancelSubscription = '/billing/cancel';
  static const String invoices = '/billing/invoices';
  
  // Provisioning
  static const String provisioningJobs = '/provisioning/jobs';
  static String provisioningJobById(String id) => '/provisioning/jobs/$id';
  static String retryJob(String id) => '/provisioning/jobs/$id/retry';
  static String cancelJob(String id) => '/provisioning/jobs/$id/cancel';
  
  // SSO
  static const String ssoToken = '/sso/erpnext/token';
  static const String ssoCallback = '/sso/erpnext/callback';
}
```

---

## 2. Models

### user.dart

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'user.freezed.dart';
part 'user.g.dart';

@freezed
class User with _$User {
  const factory User({
    required String id,
    required String email,
    @JsonKey(name: 'full_name') required String fullName,
    @JsonKey(name: 'is_active') required bool isActive,
    @JsonKey(name: 'is_superuser') required bool isSuperuser,
    @JsonKey(name: 'created_at') required DateTime createdAt,
    @JsonKey(name: 'updated_at') required DateTime updatedAt,
  }) = _User;
  
  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
}

@freezed
class UserTenant with _$UserTenant {
  const factory UserTenant({
    @JsonKey(name: 'tenant_id') required String tenantId,
    @JsonKey(name: 'tenant_name') required String tenantName,
    required String role,
    @JsonKey(name: 'is_default') required bool isDefault,
  }) = _UserTenant;
  
  factory UserTenant.fromJson(Map<String, dynamic> json) =>
      _$UserTenantFromJson(json);
}
```

### tenant.dart

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'tenant.freezed.dart';
part 'tenant.g.dart';

enum TenantStatus {
  pending,
  provisioning,
  active,
  suspended,
  cancelled,
}

@freezed
class Tenant with _$Tenant {
  const factory Tenant({
    required String id,
    required String name,
    required String slug,
    required TenantStatus status,
    @JsonKey(name: 'erpnext_site_url') String? erpnextSiteUrl,
    Map<String, dynamic>? settings,
    @JsonKey(name: 'created_at') required DateTime createdAt,
    @JsonKey(name: 'updated_at') required DateTime updatedAt,
  }) = _Tenant;
  
  factory Tenant.fromJson(Map<String, dynamic> json) => _$TenantFromJson(json);
}
```

### subscription.dart

```dart
import 'package:freezed_annotation/freezed_annotation.dart';
import 'plan.dart';

part 'subscription.freezed.dart';
part 'subscription.g.dart';

enum SubscriptionStatus {
  trial,
  active,
  @JsonValue('past_due')
  pastDue,
  cancelled,
  expired,
}

enum BillingPeriod {
  monthly,
  yearly,
}

@freezed
class Subscription with _$Subscription {
  const factory Subscription({
    required String id,
    @JsonKey(name: 'tenant_id') required String tenantId,
    @JsonKey(name: 'plan_id') required String planId,
    required SubscriptionStatus status,
    @JsonKey(name: 'billing_period') required BillingPeriod billingPeriod,
    @JsonKey(name: 'trial_ends_at') DateTime? trialEndsAt,
    @JsonKey(name: 'current_period_start') required DateTime currentPeriodStart,
    @JsonKey(name: 'current_period_end') required DateTime currentPeriodEnd,
    @JsonKey(name: 'cancelled_at') DateTime? cancelledAt,
    Plan? plan,
  }) = _Subscription;
  
  factory Subscription.fromJson(Map<String, dynamic> json) =>
      _$SubscriptionFromJson(json);
}
```

### plan.dart

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'plan.freezed.dart';
part 'plan.g.dart';

@freezed
class Plan with _$Plan {
  const factory Plan({
    required String id,
    required String name,
    required String slug,
    String? description,
    @JsonKey(name: 'price_monthly') required double priceMonthly,
    @JsonKey(name: 'price_yearly') required double priceYearly,
    required String currency,
    required Map<String, dynamic> limits,
    required List<String> features,
    @JsonKey(name: 'is_active') required bool isActive,
    @JsonKey(name: 'sort_order') required int sortOrder,
  }) = _Plan;
  
  factory Plan.fromJson(Map<String, dynamic> json) => _$PlanFromJson(json);
}
```

### provisioning_job.dart

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'provisioning_job.freezed.dart';
part 'provisioning_job.g.dart';

enum JobStatus {
  pending,
  running,
  completed,
  failed,
}

enum JobType {
  @JsonValue('create_site')
  createSite,
  @JsonValue('delete_site')
  deleteSite,
  @JsonValue('backup_site')
  backupSite,
}

@freezed
class ProvisioningJob with _$ProvisioningJob {
  const factory ProvisioningJob({
    required String id,
    @JsonKey(name: 'tenant_id') required String tenantId,
    required JobStatus status,
    @JsonKey(name: 'job_type') required JobType jobType,
    required int progress,
    String? message,
    String? error,
    @JsonKey(name: 'started_at') DateTime? startedAt,
    @JsonKey(name: 'completed_at') DateTime? completedAt,
    @JsonKey(name: 'created_at') required DateTime createdAt,
  }) = _ProvisioningJob;
  
  factory ProvisioningJob.fromJson(Map<String, dynamic> json) =>
      _$ProvisioningJobFromJson(json);
}
```

---

## 3. Services

### auth_service.dart

```dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../api/api_client.dart';
import '../api/api_endpoints.dart';
import '../models/user.dart';
import '../models/tenant.dart';
import 'dart:developer' as dev;

class AuthService {
  final ApiClient _client;
  final FlutterSecureStorage _storage;
  
  AuthService({
    required ApiClient client,
    FlutterSecureStorage? storage,
  })  : _client = client,
        _storage = storage ?? const FlutterSecureStorage();
  
  /// Register new user
  Future<AuthResponse> register({
    required String email,
    required String password,
    required String fullName,
    required String companyName,
  }) async {
    try {
      final response = await _client.post(
        ApiEndpoints.register,
        data: {
          'email': email,
          'password': password,
          'full_name': fullName,
          'company_name': companyName,
        },
      );
      
      final data = response.data['data'];
      await _saveTokens(
        accessToken: data['access_token'],
        refreshToken: data['refresh_token'],
      );
      
      return AuthResponse.fromJson(data);
    } catch (e) {
      dev.log('Register error: $e');
      rethrow;
    }
  }
  
  /// Login user
  Future<AuthResponse> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _client.post(
        ApiEndpoints.login,
        data: {
          'email': email,
          'password': password,
        },
      );
      
      final data = response.data['data'];
      await _saveTokens(
        accessToken: data['access_token'],
        refreshToken: data['refresh_token'],
      );
      
      return AuthResponse.fromJson(data);
    } catch (e) {
      dev.log('Login error: $e');
      rethrow;
    }
  }
  
  /// Logout user
  Future<void> logout() async {
    try {
      await _client.post(ApiEndpoints.logout);
    } catch (e) {
      dev.log('Logout error: $e');
    } finally {
      await _storage.deleteAll();
    }
  }
  
  /// Get current user info
  Future<UserWithTenants> getCurrentUser() async {
    final response = await _client.get(ApiEndpoints.me);
    return UserWithTenants.fromJson(response.data['data']);
  }
  
  /// Switch tenant
  Future<SwitchTenantResponse> switchTenant(String tenantId) async {
    final response = await _client.post(
      ApiEndpoints.switchTenant,
      data: {'tenant_id': tenantId},
    );
    
    final data = response.data['data'];
    await _saveTokens(
      accessToken: data['access_token'],
      refreshToken: data['refresh_token'],
    );
    
    return SwitchTenantResponse.fromJson(data);
  }
  
  /// Check if user is authenticated
  Future<bool> isAuthenticated() async {
    final token = await _storage.read(key: 'access_token');
    return token != null;
  }
  
  Future<void> _saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _storage.write(key: 'access_token', value: accessToken);
    await _storage.write(key: 'refresh_token', value: refreshToken);
  }
}

// Response models
class AuthResponse {
  final String accessToken;
  final String refreshToken;
  final User user;
  final List<UserTenant> tenants;
  final Tenant currentTenant;
  
  AuthResponse({
    required this.accessToken,
    required this.refreshToken,
    required this.user,
    required this.tenants,
    required this.currentTenant,
  });
  
  factory AuthResponse.fromJson(Map<String, dynamic> json) {
    return AuthResponse(
      accessToken: json['access_token'],
      refreshToken: json['refresh_token'],
      user: User.fromJson(json['user']),
      tenants: (json['tenants'] as List)
          .map((t) => UserTenant.fromJson(t))
          .toList(),
      currentTenant: Tenant.fromJson(json['current_tenant']),
    );
  }
}

class UserWithTenants {
  final User user;
  final List<UserTenant> tenants;
  
  UserWithTenants({required this.user, required this.tenants});
  
  factory UserWithTenants.fromJson(Map<String, dynamic> json) {
    return UserWithTenants(
      user: User.fromJson(json['user']),
      tenants: (json['tenants'] as List)
          .map((t) => UserTenant.fromJson(t))
          .toList(),
    );
  }
}

class SwitchTenantResponse {
  final String accessToken;
  final String refreshToken;
  final Tenant tenant;
  
  SwitchTenantResponse({
    required this.accessToken,
    required this.refreshToken,
    required this.tenant,
  });
  
  factory SwitchTenantResponse.fromJson(Map<String, dynamic> json) {
    return SwitchTenantResponse(
      accessToken: json['access_token'],
      refreshToken: json['refresh_token'],
      tenant: Tenant.fromJson(json['tenant']),
    );
  }
}
```

### tenant_service.dart

```dart
import '../api/api_client.dart';
import '../api/api_endpoints.dart';
import '../models/tenant.dart';
import 'dart:developer' as dev;

class TenantService {
  final ApiClient _client;
  
  TenantService({required ApiClient client}) : _client = client;
  
  /// Get all user's tenants
  Future<List<Tenant>> getTenants({int page = 1, int size = 20}) async {
    final response = await _client.get(
      ApiEndpoints.tenants,
      queryParameters: {'page': page, 'size': size},
    );
    
    return (response.data['data'] as List)
        .map((t) => Tenant.fromJson(t))
        .toList();
  }
  
  /// Get current tenant
  Future<Tenant> getCurrentTenant() async {
    final response = await _client.get(ApiEndpoints.currentTenant);
    return Tenant.fromJson(response.data['data']);
  }
  
  /// Get tenant by ID
  Future<Tenant> getTenantById(String id) async {
    final response = await _client.get(ApiEndpoints.tenantById(id));
    return Tenant.fromJson(response.data['data']);
  }
  
  /// Update tenant
  Future<Tenant> updateTenant(
    String id, {
    String? name,
    Map<String, dynamic>? settings,
  }) async {
    final response = await _client.patch(
      ApiEndpoints.tenantById(id),
      data: {
        if (name != null) 'name': name,
        if (settings != null) 'settings': settings,
      },
    );
    
    return Tenant.fromJson(response.data['data']);
  }
  
  /// Get tenant users
  Future<List<TenantUser>> getTenantUsers(
    String tenantId, {
    int page = 1,
    int size = 20,
  }) async {
    final response = await _client.get(
      ApiEndpoints.tenantUsers(tenantId),
      queryParameters: {'page': page, 'size': size},
    );
    
    return (response.data['data'] as List)
        .map((u) => TenantUser.fromJson(u))
        .toList();
  }
  
  /// Invite user to tenant
  Future<void> inviteUser(
    String tenantId, {
    required String email,
    required String role,
  }) async {
    await _client.post(
      ApiEndpoints.inviteUser(tenantId),
      data: {
        'email': email,
        'role': role,
      },
    );
  }
  
  /// Update user role
  Future<void> updateUserRole(
    String tenantId,
    String userId, {
    required String role,
  }) async {
    await _client.patch(
      ApiEndpoints.updateUserRole(tenantId, userId),
      data: {'role': role},
    );
  }
  
  /// Remove user from tenant
  Future<void> removeUser(String tenantId, String userId) async {
    await _client.delete(ApiEndpoints.updateUserRole(tenantId, userId));
  }
}

class TenantUser {
  final String userId;
  final String email;
  final String fullName;
  final String role;
  final bool isDefault;
  final DateTime joinedAt;
  
  TenantUser({
    required this.userId,
    required this.email,
    required this.fullName,
    required this.role,
    required this.isDefault,
    required this.joinedAt,
  });
  
  factory TenantUser.fromJson(Map<String, dynamic> json) {
    return TenantUser(
      userId: json['user_id'],
      email: json['email'],
      fullName: json['full_name'],
      role: json['role'],
      isDefault: json['is_default'],
      joinedAt: DateTime.parse(json['joined_at']),
    );
  }
}
```

### billing_service.dart

```dart
import '../api/api_client.dart';
import '../api/api_endpoints.dart';
import '../models/plan.dart';
import '../models/subscription.dart';
import 'dart:developer' as dev;

class BillingService {
  final ApiClient _client;
  
  BillingService({required ApiClient client}) : _client = client;
  
  /// Get all available plans
  Future<List<Plan>> getPlans() async {
    final response = await _client.get(ApiEndpoints.plans);
    return (response.data['data'] as List)
        .map((p) => Plan.fromJson(p))
        .toList();
  }
  
  /// Get current subscription
  Future<Subscription> getSubscription() async {
    final response = await _client.get(ApiEndpoints.subscription);
    return Subscription.fromJson(response.data['data']);
  }
  
  /// Create checkout session
  Future<CheckoutResponse> createCheckout({
    required String planId,
    required BillingPeriod billingPeriod,
    required String successUrl,
    required String cancelUrl,
  }) async {
    final response = await _client.post(
      ApiEndpoints.checkout,
      data: {
        'plan_id': planId,
        'billing_period': billingPeriod.name,
        'payment_provider': 'stripe',
        'success_url': successUrl,
        'cancel_url': cancelUrl,
      },
    );
    
    return CheckoutResponse.fromJson(response.data['data']);
  }
  
  /// Cancel subscription
  Future<void> cancelSubscription({
    String? reason,
    bool cancelAtPeriodEnd = true,
  }) async {
    await _client.post(
      ApiEndpoints.cancelSubscription,
      data: {
        if (reason != null) 'reason': reason,
        'cancel_at_period_end': cancelAtPeriodEnd,
      },
    );
  }
  
  /// Get payment history
  Future<List<PaymentEvent>> getInvoices({
    int page = 1,
    int size = 20,
  }) async {
    final response = await _client.get(
      ApiEndpoints.invoices,
      queryParameters: {'page': page, 'size': size},
    );
    
    return (response.data['data'] as List)
        .map((e) => PaymentEvent.fromJson(e))
        .toList();
  }
}

class CheckoutResponse {
  final String checkoutUrl;
  final String sessionId;
  
  CheckoutResponse({
    required this.checkoutUrl,
    required this.sessionId,
  });
  
  factory CheckoutResponse.fromJson(Map<String, dynamic> json) {
    return CheckoutResponse(
      checkoutUrl: json['checkout_url'],
      sessionId: json['session_id'],
    );
  }
}

class PaymentEvent {
  final String id;
  final String eventType;
  final double amount;
  final String currency;
  final DateTime createdAt;
  
  PaymentEvent({
    required this.id,
    required this.eventType,
    required this.amount,
    required this.currency,
    required this.createdAt,
  });
  
  factory PaymentEvent.fromJson(Map<String, dynamic> json) {
    return PaymentEvent(
      id: json['id'],
      eventType: json['event_type'],
      amount: json['amount'].toDouble(),
      currency: json['currency'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
```

### provisioning_service.dart

```dart
import '../api/api_client.dart';
import '../api/api_endpoints.dart';
import '../models/provisioning_job.dart';
import 'dart:developer' as dev;

class ProvisioningService {
  final ApiClient _client;
  
  ProvisioningService({required ApiClient client}) : _client = client;
  
  /// Get all provisioning jobs
  Future<List<ProvisioningJob>> getJobs({
    int page = 1,
    int size = 20,
  }) async {
    final response = await _client.get(
      ApiEndpoints.provisioningJobs,
      queryParameters: {'page': page, 'size': size},
    );
    
    return (response.data['data'] as List)
        .map((j) => ProvisioningJob.fromJson(j))
        .toList();
  }
  
  /// Get job by ID
  Future<ProvisioningJob> getJobById(String id) async {
    final response = await _client.get(
      ApiEndpoints.provisioningJobById(id),
    );
    
    return ProvisioningJob.fromJson(response.data['data']);
  }
  
  /// Create new provisioning job
  Future<ProvisioningJob> createJob(JobType jobType) async {
    final response = await _client.post(
      ApiEndpoints.provisioningJobs,
      data: {'job_type': jobType.name},
    );
    
    return ProvisioningJob.fromJson(response.data['data']);
  }
  
  /// Retry failed job
  Future<ProvisioningJob> retryJob(String id) async {
    final response = await _client.post(
      ApiEndpoints.retryJob(id),
    );
    
    return ProvisioningJob.fromJson(response.data['data']);
  }
  
  /// Cancel job
  Future<void> cancelJob(String id) async {
    await _client.post(ApiEndpoints.cancelJob(id));
  }
}
```

### sso_service.dart

```dart
import '../api/api_client.dart';
import '../api/api_endpoints.dart';
import 'dart:developer' as dev;

class SSOService {
  final ApiClient _client;
  
  SSOService({required ApiClient client}) : _client = client;
  
  /// Generate SSO token for ERPNext login
  Future<SSOTokenResponse> generateToken() async {
    final response = await _client.post(ApiEndpoints.ssoToken);
    return SSOTokenResponse.fromJson(response.data['data']);
  }
}

class SSOTokenResponse {
  final String ssoUrl;
  final String token;
  final DateTime expiresAt;
  
  SSOTokenResponse({
    required this.ssoUrl,
    required this.token,
    required this.expiresAt,
  });
  
  factory SSOTokenResponse.fromJson(Map<String, dynamic> json) {
    return SSOTokenResponse(
      ssoUrl: json['sso_url'],
      token: json['token'],
      expiresAt: DateTime.parse(json['expires_at']),
    );
  }
}
```

---

## 4. Real-time Service (Socket.IO)

### realtime_service.dart

```dart
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:developer' as dev;

class RealtimeService {
  static const String baseUrl = 'http://localhost:8000/ws';
  
  IO.Socket? _socket;
  final FlutterSecureStorage _storage;
  
  // Callbacks
  Function(Map<String, dynamic>)? onProvisioningUpdate;
  Function(Map<String, dynamic>)? onProvisioningCompleted;
  Function(Map<String, dynamic>)? onProvisioningFailed;
  Function(Map<String, dynamic>)? onNotification;
  Function(Map<String, dynamic>)? onSubscriptionUpdated;
  Function(Map<String, dynamic>)? onPaymentReceived;
  
  RealtimeService({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();
  
  /// Connect to Socket.IO server
  Future<void> connect() async {
    final token = await _storage.read(key: 'access_token');
    if (token == null) {
      dev.log('No access token found');
      return;
    }
    
    _socket = IO.io(
      baseUrl,
      IO.OptionBuilder()
          .setTransports(['websocket'])
          .setPath('/socket.io')
          .setAuth({'token': token})
          .enableAutoConnect()
          .build(),
    );
    
    _setupListeners();
    _socket!.connect();
  }
  
  void _setupListeners() {
    // Connection events
    _socket!.on('connect', (_) {
      dev.log('Socket.IO connected');
    });
    
    _socket!.on('connected', (data) {
      dev.log('Socket.IO authenticated: $data');
    });
    
    _socket!.on('disconnect', (_) {
      dev.log('Socket.IO disconnected');
    });
    
    _socket!.on('error', (data) {
      dev.log('Socket.IO error: $data');
    });
    
    // Provisioning events
    _socket!.on('status:update', (data) {
      dev.log('Provisioning update: $data');
      onProvisioningUpdate?.call(data);
    });
    
    _socket!.on('status:completed', (data) {
      dev.log('Provisioning completed: $data');
      onProvisioningCompleted?.call(data);
    });
    
    _socket!.on('status:failed', (data) {
      dev.log('Provisioning failed: $data');
      onProvisioningFailed?.call(data);
    });
    
    // Notification events
    _socket!.on('notification:new', (data) {
      dev.log('New notification: $data');
      onNotification?.call(data);
    });
    
    // Billing events
    _socket!.on('subscription:updated', (data) {
      dev.log('Subscription updated: $data');
      onSubscriptionUpdated?.call(data);
    });
    
    _socket!.on('payment:received', (data) {
      dev.log('Payment received: $data');
      onPaymentReceived?.call(data);
    });
  }
  
  /// Mark notification as read
  void markNotificationRead(String notificationId) {
    _socket?.emit('notification_read', {'notification_id': notificationId});
  }
  
  /// Disconnect from Socket.IO server
  void disconnect() {
    _socket?.disconnect();
    _socket?.dispose();
    _socket = null;
  }
  
  /// Check if connected
  bool get isConnected => _socket?.connected ?? false;
}
```

---

## 5. Usage Examples

### Authentication Flow

```dart
// Login
final authService = AuthService(client: apiClient);

try {
  final response = await authService.login(
    email: 'user@example.com',
    password: 'SecurePass123',
  );
  
  // Navigate to dashboard
  Navigator.pushReplacementNamed(context, '/dashboard');
} catch (e) {
  // Show error
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Login failed: $e')),
  );
}
```

### Provisioning with Real-time Updates

```dart
class ProvisioningScreen extends StatefulWidget {
  @override
  _ProvisioningScreenState createState() => _ProvisioningScreenState();
}

class _ProvisioningScreenState extends State<ProvisioningScreen> {
  final RealtimeService _realtime = RealtimeService();
  double _progress = 0.0;
  String _message = 'Starting provisioning...';
  
  @override
  void initState() {
    super.initState();
    _setupRealtime();
    _startProvisioning();
  }
  
  void _setupRealtime() {
    _realtime.onProvisioningUpdate = (data) {
      setState(() {
        _progress = data['progress'].toDouble() / 100;
        _message = data['message'] ?? '';
      });
    };
    
    _realtime.onProvisioningCompleted = (data) {
      setState(() {
        _progress = 1.0;
        _message = 'Site ready!';
      });
      
      // Navigate to ERPNext
      final url = data['erpnext_url'];
      // Launch URL
    };
    
    _realtime.onProvisioningFailed = (data) {
      setState(() {
        _message = 'Failed: ${data['error']}';
      });
    };
    
    _realtime.connect();
  }
  
  Future<void> _startProvisioning() async {
    final service = ProvisioningService(client: apiClient);
    await service.createJob(JobType.createSite);
  }
  
  @override
  void dispose() {
    _realtime.disconnect();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Provisioning')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(value: _progress),
            SizedBox(height: 20),
            Text(_message),
            Text('${(_progress * 100).toInt()}%'),
          ],
        ),
      ),
    );
  }
}
```

### Billing Flow

```dart
// Get plans
final billingService = BillingService(client: apiClient);
final plans = await billingService.getPlans();

// Create checkout
final checkout = await billingService.createCheckout(
  planId: selectedPlan.id,
  billingPeriod: BillingPeriod.monthly,
  successUrl: 'https://app.erpmax.com/billing/success',
  cancelUrl: 'https://app.erpmax.com/billing/cancel',
);

// Open checkout URL in browser
await launchUrl(Uri.parse(checkout.checkoutUrl));
```

---

## 6. Error Handling

### API Response Structure

```dart
class ApiResponse<T> {
  final String status;
  final T? data;
  final ApiError? error;
  final PaginationInfo? pagination;
  
  bool get isSuccess => status == 'success';
  
  ApiResponse({
    required this.status,
    this.data,
    this.error,
    this.pagination,
  });
}

class ApiError {
  final String message;
  final String? code;
  final Map<String, dynamic>? details;
  
  ApiError({
    required this.message,
    this.code,
    this.details,
  });
}
```

### Error Handling Example

```dart
try {
  final user = await authService.getCurrentUser();
} on DioException catch (e) {
  if (e.response?.statusCode == 401) {
    // Unauthorized - redirect to login
    Navigator.pushReplacementNamed(context, '/login');
  } else if (e.response?.statusCode == 403) {
    // Forbidden
    showError('You don\'t have permission');
  } else if (e.response?.statusCode == 404) {
    // Not found
    showError('Resource not found');
  } else {
    // Other errors
    showError('Something went wrong: ${e.message}');
  }
}
```

---

## 7. Testing

### Unit Tests

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';

void main() {
  group('AuthService', () {
    late AuthService authService;
    late MockApiClient mockClient;
    
    setUp(() {
      mockClient = MockApiClient();
      authService = AuthService(client: mockClient);
    });
    
    test('login success', () async {
      // Arrange
      when(mockClient.post(any, data: anyNamed('data')))
          .thenAnswer((_) async => Response(
                data: {
                  'data': {
                    'access_token': 'token',
                    'refresh_token': 'refresh',
                    'user': {...},
                    'tenants': [...],
                    'current_tenant': {...},
                  }
                },
                statusCode: 200,
              ));
      
      // Act
      final response = await authService.login(
        email: 'test@example.com',
        password: 'password',
      );
      
      // Assert
      expect(response.accessToken, 'token');
      expect(response.user.email, 'test@example.com');
    });
  });
}
```

---

## 8. Security Best Practices

### Token Storage

- ✅ Використовуйте `flutter_secure_storage` для JWT токенів
- ✅ Ніколи не зберігайте токени в `SharedPreferences`
- ✅ Очищайте токени при logout

### HTTPS

- ✅ Завжди використовуйте HTTPS на production
- ✅ Перевіряйте SSL сертифікати

### Token Refresh

- ✅ Автоматичний refresh при 401
- ✅ Retry failed requests після refresh
- ✅ Logout при failed refresh

### Input Validation

- ✅ Валідуйте всі user inputs
- ✅ Використовуйте Pydantic-like валідацію
- ✅ Показуйте зрозумілі помилки

---

## 9. Performance Optimization

### Caching

```dart
import 'package:shared_preferences/shared_preferences.dart';

class CacheService {
  static const String _plansKey = 'cached_plans';
  
  Future<void> cachePlans(List<Plan> plans) async {
    final prefs = await SharedPreferences.getInstance();
    final json = plans.map((p) => p.toJson()).toList();
    await prefs.setString(_plansKey, jsonEncode(json));
  }
  
  Future<List<Plan>?> getCachedPlans() async {
    final prefs = await SharedPreferences.getInstance();
    final json = prefs.getString(_plansKey);
    if (json == null) return null;
    
    return (jsonDecode(json) as List)
        .map((p) => Plan.fromJson(p))
        .toList();
  }
}
```

### Pagination

```dart
class PaginatedList<T> {
  final List<T> items;
  final int total;
  final int page;
  final int size;
  final int pages;
  
  bool get hasMore => page < pages;
  
  PaginatedList({
    required this.items,
    required this.total,
    required this.page,
    required this.size,
    required this.pages,
  });
}
```

---

## 10. Troubleshooting

### Common Issues

**1. Connection Timeout**

```dart
// Increase timeout
final dio = Dio(BaseOptions(
  connectTimeout: const Duration(seconds: 60),
  receiveTimeout: const Duration(seconds: 60),
));
```

**2. SSL Certificate Error**

```dart
// Development only - bypass SSL
(_dio.httpClientAdapter as DefaultHttpClientAdapter).onHttpClientCreate =
    (client) {
  client.badCertificateCallback = (cert, host, port) => true;
  return client;
};
```

**3. Socket.IO Not Connecting**

- Перевірте JWT token
- Перевірте CORS налаштування
- Перевірте WebSocket support

---

## Додаткові ресурси

- **API Documentation**: `http://localhost:8000/docs`
- **Dio Package**: <https://pub.dev/packages/dio>
- **Socket.IO Client**: <https://pub.dev/packages/socket_io_client>
- **Freezed**: <https://pub.dev/packages/freezed>
- **Riverpod**: <https://pub.dev/packages/flutter_riverpod>

---

**Дата:** 16 грудня 2024  
**Версія API:** v1  
**Статус:** Production Ready
