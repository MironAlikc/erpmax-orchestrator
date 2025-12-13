from __future__ import annotations

import json
from typing import Any

import aio_pika

from app.core.config import get_settings


def get_rabbitmq_url() -> str:
    settings = get_settings()

    if settings.rabbitmq_url:
        return settings.rabbitmq_url

    user = settings.rabbitmq_user
    password = settings.rabbitmq_password
    host = settings.rabbitmq_host
    port = settings.rabbitmq_port

    return f"amqp://{user}:{password}@{host}:{port}/"


async def publish_json(*, queue_name: str, message: dict[str, Any]) -> None:
    url = get_rabbitmq_url()

    connection = await aio_pika.connect_robust(url)
    try:
        channel = await connection.channel()
        await channel.declare_queue(queue_name, durable=True)

        body = json.dumps(message).encode("utf-8")
        await channel.default_exchange.publish(
            aio_pika.Message(body=body, content_type="application/json"),
            routing_key=queue_name,
        )
    finally:
        await connection.close()
