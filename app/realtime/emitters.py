"""Helper functions for emitting Socket.IO events"""

import logging
from typing import Any, Dict
from uuid import UUID

from app.realtime.server import sio

log = logging.getLogger(__name__)


async def emit_to_user(
    user_id: UUID, event: str, data: Dict[str, Any], namespace: str = "/"
):
    """
    Emit event to specific user

    Args:
        user_id: User UUID
        event: Event name
        data: Event data
        namespace: Socket.IO namespace (default: '/')
    """
    room = f"user:{user_id}"
    try:
        await sio.emit(event, data, room=room, namespace=namespace)
        log.debug(f"Emitted {event} to user {user_id} in namespace {namespace}")
    except Exception as e:
        log.error(f"Error emitting {event} to user {user_id}: {str(e)}")


async def emit_to_tenant(
    tenant_id: UUID, event: str, data: Dict[str, Any], namespace: str = "/"
):
    """
    Emit event to all users in tenant

    Args:
        tenant_id: Tenant UUID
        event: Event name
        data: Event data
        namespace: Socket.IO namespace (default: '/')
    """
    room = f"tenant:{tenant_id}"
    try:
        await sio.emit(event, data, room=room, namespace=namespace)
        log.debug(f"Emitted {event} to tenant {tenant_id} in namespace {namespace}")
    except Exception as e:
        log.error(f"Error emitting {event} to tenant {tenant_id}: {str(e)}")


# Provisioning events
async def emit_provisioning_status(
    tenant_id: UUID, status: str, progress: int, message: str | None = None
):
    """
    Emit provisioning status update

    Args:
        tenant_id: Tenant UUID
        status: Job status (pending, running, completed, failed)
        progress: Progress percentage (0-100)
        message: Optional status message
    """
    await emit_to_tenant(
        tenant_id,
        "status:update",
        {
            "tenant_id": str(tenant_id),
            "status": status,
            "progress": progress,
            "message": message,
        },
        namespace="/provisioning",
    )


async def emit_provisioning_completed(tenant_id: UUID, erpnext_url: str):
    """
    Emit provisioning completed event

    Args:
        tenant_id: Tenant UUID
        erpnext_url: ERPNext site URL
    """
    await emit_to_tenant(
        tenant_id,
        "status:completed",
        {"tenant_id": str(tenant_id), "erpnext_url": erpnext_url},
        namespace="/provisioning",
    )


async def emit_provisioning_failed(tenant_id: UUID, error: str):
    """
    Emit provisioning failed event

    Args:
        tenant_id: Tenant UUID
        error: Error message
    """
    await emit_to_tenant(
        tenant_id,
        "status:failed",
        {"tenant_id": str(tenant_id), "error": error},
        namespace="/provisioning",
    )


# Notification events
async def emit_notification(
    user_id: UUID,
    notification_id: UUID,
    title: str,
    message: str,
    notification_type: str = "info",
):
    """
    Emit new notification to user

    Args:
        user_id: User UUID
        notification_id: Notification UUID
        title: Notification title
        message: Notification message
        notification_type: Type (info, success, warning, error)
    """
    await emit_to_user(
        user_id,
        "notification:new",
        {
            "id": str(notification_id),
            "title": title,
            "message": message,
            "type": notification_type,
        },
        namespace="/notifications",
    )


# Billing events
async def emit_subscription_updated(tenant_id: UUID, subscription: Dict[str, Any]):
    """
    Emit subscription updated event

    Args:
        tenant_id: Tenant UUID
        subscription: Subscription data
    """
    await emit_to_tenant(
        tenant_id,
        "subscription:updated",
        {"subscription": subscription},
        namespace="/billing",
    )


async def emit_subscription_expiring(tenant_id: UUID, days_left: int):
    """
    Emit subscription expiring warning

    Args:
        tenant_id: Tenant UUID
        days_left: Days until expiration
    """
    await emit_to_tenant(
        tenant_id,
        "subscription:expiring",
        {"days_left": days_left},
        namespace="/billing",
    )


async def emit_payment_received(tenant_id: UUID, amount: float, currency: str):
    """
    Emit payment received event

    Args:
        tenant_id: Tenant UUID
        amount: Payment amount
        currency: Currency code
    """
    await emit_to_tenant(
        tenant_id,
        "payment:received",
        {"amount": amount, "currency": currency},
        namespace="/billing",
    )
