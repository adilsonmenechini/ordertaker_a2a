"""Cozinha agent — streaming preparation progress via SSE."""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role

from models.order import OrderStatus, list_orders


class CozinhaExecutor(AgentExecutor):
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        for part in context.message.parts:
            if hasattr(part, "text") and part.text:
                break

        orders = list_orders()
        active = [o for o in orders if o.status in (OrderStatus.FILA, OrderStatus.COZINHA)]

        if not active:
            msg = "🍳 Nenhum pedido na cozinha no momento."
            await event_queue.enqueue_event(Message(role=Role.ROLE_AGENT, parts=[Part(text=msg)]))
            return

        order = active[-1]
        order.advance()  # FILA -> COZINHA

        steps = [
            "🔥 Aquecendo o óleo...",
            "🥟 Massa sendo aberta...",
            "🥩 Recheio sendo preparado...",
            "📐 Montando o pastel...",
            "🍟 Fritando... golden & crispy!",
            "✅ Cozinha finalizou o pedido!",
        ]

        for step in steps:
            await event_queue.enqueue_event(Message(role=Role.ROLE_AGENT, parts=[Part(text=step)]))
            await asyncio.sleep(1.5)

        order.advance()  # COZINHA -> PREPARO
        await event_queue.enqueue_event(
            Message(
                role=Role.ROLE_AGENT,
                parts=[Part(text=f"🎯 Pedido #{order.id} saiu da cozinha e está no preparo.")],
            )
        )
