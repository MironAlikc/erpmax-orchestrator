"""Socket.IO server configuration"""

import socketio
from app.core.config import get_settings

settings = get_settings()

# Create AsyncServer instance
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",  # Configure based on settings.allowed_origins in production
    logger=True,
    engineio_logger=False,
)

# Redis adapter for multi-instance support (production)
if settings.environment == "production":
    mgr = socketio.AsyncRedisManager(
        f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/1"
    )
    sio = socketio.AsyncServer(
        async_mode="asgi",
        client_manager=mgr,
        cors_allowed_origins=settings.allowed_origins,
        logger=True,
        engineio_logger=False,
    )

# Create ASGI app
socket_app = socketio.ASGIApp(sio, socketio_path="/socket.io")
