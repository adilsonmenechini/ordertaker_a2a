"""Entrega agent — confirms delivery."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role

from models.order import OrderStatus, list_orders


class EntregaExecutor(AgentExecutor):
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        orders = list_orders()
        active = [o for o in orders if o.status == OrderStatus.ENTREGA]

        if not active:
            await event_queue.enqueue_event(
                Message(role=Role.agent, parts=[Part(text="🚚 Nenhum pedido para entregar.")])
            )
            return

        order = active[-1]
        order.advance()  # ENTREGA -> CONCLUIDO

        await event_queue.enqueue_event(
            Message(
                role=Role.agent,
                parts=[
                    Part(
                        text=(
                            f"🎉 Pedido #{order.id} entregue com sucesso!\n"
                            f"Cliente: {order.cliente_nome}\n"
                            f"Status: CONCLUÍDO\n"
                            f"Obrigado pela preferência! 🥟"
                        )
                    )
                ],
            )
        )
