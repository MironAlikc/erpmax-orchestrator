"""Billing namespace handlers"""

import logging
import socketio
from app.realtime.server import sio

log = logging.getLogger(__name__)


class BillingNamespace(socketio.AsyncNamespace):
    """Billing namespace handler"""

    async def on_connect(self, sid, environ, auth):
        """Handle connection to billing namespace"""
        log.info(f"Client connected to /billing: {sid}")

    async def on_disconnect(self, sid):
        """Handle disconnection from billing namespace"""
        log.info(f"Client disconnected from /billing: {sid}")


# Register namespace
sio.register_namespace(BillingNamespace("/billing"))
