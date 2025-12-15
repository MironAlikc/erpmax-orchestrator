# Real-time Service (Socket.IO)

## Purpose

Real-time bidirectional communication between ERPMax Orchestrator and clients (Flutter app).

- Instant provisioning status updates
- Live billing notifications
- Real-time system notifications
- Multi-instance support via Redis adapter

---

## Architecture

```text
Flutter Client <---> Socket.IO Server <---> Redis Adapter
                           |
                           v
                    RabbitMQ Workers
```

---

## Components

### Server

- `app/realtime/server.py` — AsyncServer instance
- `app/realtime/events.py` — Connection/disconnection handlers
- `app/realtime/emitters.py` — Helper functions for emitting events

### Namespaces

- `app/realtime/namespaces/notifications.py` — `/notifications`
- `app/realtime/namespaces/provisioning.py` — `/provisioning`
- `app/realtime/namespaces/billing.py` — `/billing`

### Integration

- Mounted in `app/main.py` under `/ws`
- Provisioning worker emits real-time updates

---

## Connection

### Endpoint

```text
ws://localhost:8000/ws/socket.io
```

Production:

```text
wss://api.erpmax.com/ws/socket.io
```

### Authentication

Clients must provide JWT token during connection:

```javascript
const socket = io('http://localhost:8000/ws', {
  path: '/socket.io',
  auth: {
    token: 'your_jwt_token_here'
  }
});
```

### Connection Flow

1. Client connects with JWT token
2. Server validates token
3. Server extracts `user_id` and `tenant_id`
4. Client auto-joins rooms:
   - `user:{user_id}` — personal notifications
   - `tenant:{tenant_id}` — tenant-wide events
5. Server emits `connected` event

---

## Events

### Root Namespace (`/`)

| Event | Direction | Payload | Description |
|-------|-----------|---------|-------------|
| `connect` | C→S | `{token}` | Authenticate with JWT |
| `connected` | S→C | `{message, user_id, tenant_id}` | Connection confirmed |
| `disconnect` | C→S | - | Cleanup |
| `error` | S→C | `{message}` | Error notification |
| `ping` | C→S | - | Keepalive |
| `pong` | S→C | - | Keepalive response |

### Notifications Namespace (`/notifications`)

| Event | Direction | Payload | Description |
|-------|-----------|---------|-------------|
| `notification:new` | S→C | `{id, title, message, type, created_at}` | New notification |
| `notification_read` | C→S | `{notification_id}` | Mark as read |
| `notification_read_confirmed` | S→C | `{notification_id}` | Read confirmed |

### Provisioning Namespace (`/provisioning`)

| Event | Direction | Payload | Description |
|-------|-----------|---------|-------------|
| `status:update` | S→C | `{tenant_id, status, progress, message}` | Progress update |
| `status:completed` | S→C | `{tenant_id, erpnext_url}` | Site ready |
| `status:failed` | S→C | `{tenant_id, error}` | Provisioning failed |

### Billing Namespace (`/billing`)

| Event | Direction | Payload | Description |
|-------|-----------|---------|-------------|
| `subscription:updated` | S→C | `{subscription}` | Plan changed |
| `subscription:expiring` | S→C | `{days_left}` | Expiration warning |
| `payment:received` | S→C | `{amount, currency}` | Payment confirmed |

**Legend:** C→S (Client to Server), S→C (Server to Client)

---

## Rooms Strategy

Clients automatically join rooms based on JWT:

- `user:{user_id}` — personal notifications
- `tenant:{tenant_id}` — tenant-wide events

Events can be emitted to:

- Specific user (via `user:{user_id}` room)
- All tenant users (via `tenant:{tenant_id}` room)

---

## Emitter Functions

Helper functions in `app/realtime/emitters.py`:

### General

```python
await emit_to_user(user_id, event, data, namespace='/')
await emit_to_tenant(tenant_id, event, data, namespace='/')
```

### Provisioning

```python
await emit_provisioning_status(tenant_id, status, progress, message)
await emit_provisioning_completed(tenant_id, erpnext_url)
await emit_provisioning_failed(tenant_id, error)
```

### Notifications

```python
await emit_notification(user_id, notification_id, title, message, type)
```

### Billing

```python
await emit_subscription_updated(tenant_id, subscription)
await emit_subscription_expiring(tenant_id, days_left)
await emit_payment_received(tenant_id, amount, currency)
```

---

## Client Example (JavaScript)

```javascript
import io from 'socket.io-client';

// Connect
const socket = io('http://localhost:8000/ws', {
  path: '/socket.io',
  auth: {
    token: localStorage.getItem('access_token')
  }
});

// Connection events
socket.on('connected', (data) => {
  console.log('Connected:', data);
});

socket.on('error', (data) => {
  console.error('Socket error:', data.message);
});

// Provisioning events
const provisioningSocket = io('http://localhost:8000/ws/provisioning', {
  path: '/socket.io',
  auth: {
    token: localStorage.getItem('access_token')
  }
});

provisioningSocket.on('status:update', (data) => {
  console.log('Provisioning progress:', data.progress + '%');
  updateProgressBar(data.progress);
});

provisioningSocket.on('status:completed', (data) => {
  console.log('Site ready:', data.erpnext_url);
  redirectToSite(data.erpnext_url);
});

provisioningSocket.on('status:failed', (data) => {
  console.error('Provisioning failed:', data.error);
  showError(data.error);
});

// Notifications
const notificationsSocket = io('http://localhost:8000/ws/notifications', {
  path: '/socket.io',
  auth: {
    token: localStorage.getItem('access_token')
  }
});

notificationsSocket.on('notification:new', (data) => {
  showNotification(data.title, data.message, data.type);
});

// Mark notification as read
notificationsSocket.emit('notification_read', {
  notification_id: 'uuid-here'
});
```

---

## Client Example (Flutter/Dart)

```dart
import 'package:socket_io_client/socket_io_client.dart' as IO;

class SocketService {
  late IO.Socket socket;
  
  void connect(String token) {
    socket = IO.io('http://localhost:8000/ws', <String, dynamic>{
      'path': '/socket.io',
      'transports': ['websocket'],
      'auth': {'token': token},
    });
    
    socket.on('connected', (data) {
      print('Connected: $data');
    });
    
    socket.on('error', (data) {
      print('Error: ${data['message']}');
    });
    
    // Provisioning events
    socket.on('status:update', (data) {
      print('Progress: ${data['progress']}%');
    });
    
    socket.on('status:completed', (data) {
      print('Site ready: ${data['erpnext_url']}');
    });
    
    socket.connect();
  }
  
  void disconnect() {
    socket.disconnect();
  }
}
```

---

## Configuration

### Environment Variables

```bash
# Redis (for multi-instance support in production)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password

# Environment
ENVIRONMENT=production  # Enables Redis adapter
```

### Server Settings

In `app/realtime/server.py`:

- **Development**: In-memory adapter (single instance)
- **Production**: Redis adapter (multi-instance support)

---

## Testing

### Manual Testing

1. Start server:

```bash
uvicorn app.main:app --reload
```

1. Connect via browser console:

```javascript
const socket = io('http://localhost:8000/ws', {
  path: '/socket.io',
  auth: {
    token: 'your_jwt_token'
  }
});

socket.on('connected', console.log);
```

1. Trigger provisioning job via API
1. Watch real-time updates in console

### Testing Tools

- **Socket.IO Client Tool**: <https://amritb.github.io/socketio-client-tool/>
- **Postman**: Supports WebSocket connections
- **Browser DevTools**: Network tab → WS filter

---

## Production Considerations

### Redis Adapter

Required for horizontal scaling:

```python
# Automatically enabled when ENVIRONMENT=production
mgr = socketio.AsyncRedisManager(
    f'redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/1'
)
```

### CORS

Update `cors_allowed_origins` in production:

```python
cors_allowed_origins=settings.allowed_origins
```

### Load Balancing

Enable sticky sessions for WebSocket connections:

**Nginx:**

```nginx
upstream socket_io {
    ip_hash;  # Sticky sessions
    server app1:8000;
    server app2:8000;
}
```

### Monitoring

- Track active connections
- Monitor room sizes
- Log connection/disconnection events
- Alert on connection failures

---

## Limitations / Next steps

- Add reconnection logic with exponential backoff
- Implement message acknowledgments
- Add rate limiting per connection
- Create notification persistence layer
- Add typing indicators for chat features
- Implement presence (online/offline status)
- Add message history on reconnect
