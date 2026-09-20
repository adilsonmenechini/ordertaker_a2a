"""Preparo agent — long-running task with progress polling."""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role

from models.order import OrderStatus, list_orders


class PreparoExecutor(AgentExecutor):
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        for part in context.message.parts:
            if hasattr(part, "text") and part.text:
                break

        orders = list_orders()
        active = [o for o in orders if o.status == OrderStatus.PREPARO]

        if not active:
            await event_queue.enqueue_event(
                Message(role=Role.ROLE_AGENT, parts=[Part(text="📦 Nenhum pedido para preparar.")])
            )
            return

        order = active[-1]

        steps = [
            "📦 Enfatando a embalagem...",
            "🏷️ Colocando etiqueta do pedido...",
            "✅ Pronto para entrega!",
        ]

        for msg in steps:
            await event_queue.enqueue_event(Message(role=Role.ROLE_AGENT, parts=[Part(text=msg)]))
            await asyncio.sleep(2)

        order.advance()  # PREPARO -> ENTREGA
        await event_queue.enqueue_event(
            Message(
                role=Role.ROLE_AGENT,
                parts=[Part(text=f"🚗 Pedido #{order.id} saiu para entrega!")],
            )
        )
