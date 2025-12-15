"""Socket.IO event handlers"""

import logging
from uuid import UUID

from jose import JWTError

from app.realtime.server import sio
from app.core.security import verify_token
from app.core.exceptions import credentials_exception

log = logging.getLogger(__name__)


@sio.event
async def connect(sid, environ, auth):
    """
    Handle client connection

    Args:
        sid: Session ID
        environ: WSGI environment
        auth: Authentication data (should contain 'token')
    """
    try:
        # Validate JWT token
        if not auth or "token" not in auth:
            log.warning(f"Connection attempt without token: {sid}")
            raise credentials_exception("Authentication required")

        token = auth["token"]

        try:
            payload = verify_token(token, token_type="access")
        except JWTError as e:
            log.warning(f"Invalid token for connection: {sid} - {str(e)}")
            raise credentials_exception("Invalid token")

        # Extract user and tenant info from token
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")

        if not user_id or not tenant_id:
            log.warning(f"Missing user_id or tenant_id in token: {sid}")
            raise credentials_exception("Invalid token payload")

        # Store session data
        async with sio.session(sid) as session:
            session["user_id"] = user_id
            session["tenant_id"] = tenant_id
            session["authenticated"] = True

        # Join user and tenant rooms
        await sio.enter_room(sid, f"user:{user_id}")
        await sio.enter_room(sid, f"tenant:{tenant_id}")

        log.info(f"Client connected: {sid} (user: {user_id}, tenant: {tenant_id})")

        # Send connection confirmation
        await sio.emit(
            "connected",
            {
                "message": "Successfully connected to ERPMax Orchestrator",
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
            room=sid,
        )

    except Exception as e:
        log.error(f"Connection error for {sid}: {str(e)}")
        await sio.emit("error", {"message": str(e)}, room=sid)
        return False


@sio.event
async def disconnect(sid):
    """
    Handle client disconnection

    Args:
        sid: Session ID
    """
    try:
        async with sio.session(sid) as session:
            user_id = session.get("user_id")
            tenant_id = session.get("tenant_id")

        log.info(f"Client disconnected: {sid} (user: {user_id}, tenant: {tenant_id})")

    except Exception as e:
        log.error(f"Disconnect error for {sid}: {str(e)}")


@sio.event
async def ping(sid):
    """
    Handle ping event (keepalive)

    Args:
        sid: Session ID
    """
    await sio.emit("pong", room=sid)
