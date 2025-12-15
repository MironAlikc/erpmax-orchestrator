"""Provisioning namespace handlers"""

import logging
import socketio
from app.realtime.server import sio

log = logging.getLogger(__name__)


class ProvisioningNamespace(socketio.AsyncNamespace):
    """Provisioning namespace handler"""

    async def on_connect(self, sid, environ, auth):
        """Handle connection to provisioning namespace"""
        log.info(f"Client connected to /provisioning: {sid}")

    async def on_disconnect(self, sid):
        """Handle disconnection from provisioning namespace"""
        log.info(f"Client disconnected from /provisioning: {sid}")


# Register namespace
sio.register_namespace(ProvisioningNamespace("/provisioning"))
