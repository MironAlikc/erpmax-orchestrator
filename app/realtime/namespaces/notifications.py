"""Notifications namespace handlers"""

import logging
import socketio
from app.realtime.server import sio

log = logging.getLogger(__name__)


class NotificationsNamespace(socketio.AsyncNamespace):
    """Notifications namespace handler"""

    async def on_connect(self, sid, environ, auth):
        """Handle connection to notifications namespace"""
        log.info(f"Client connected to /notifications: {sid}")

    async def on_disconnect(self, sid):
        """Handle disconnection from notifications namespace"""
        log.info(f"Client disconnected from /notifications: {sid}")

    async def on_notification_read(self, sid, data):
        """
        Mark notification as read

        Args:
            sid: Session ID
            data: {notification_id: str}
        """
        try:
            notification_id = data.get("notification_id")

            if not notification_id:
                await self.emit(
                    "error", {"message": "notification_id required"}, room=sid
                )
                return

            # TODO: Update notification status in database
            log.info(f"Notification {notification_id} marked as read by {sid}")

            await self.emit(
                "notification_read_confirmed",
                {"notification_id": notification_id},
                room=sid,
            )

        except Exception as e:
            log.error(f"Error marking notification as read: {str(e)}")
            await self.emit("error", {"message": str(e)}, room=sid)


# Register namespace
sio.register_namespace(NotificationsNamespace("/notifications"))
