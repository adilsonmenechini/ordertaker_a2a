"""Fila agent — receives order, places in queue, returns position."""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role

from models.order import BordaType, PastelItem, SaborType, create_order

_queue_counter = 0


def parse_order_text(text: str) -> tuple[str, list[PastelItem]]:
    """Simple deterministic parser for order text."""
    global _queue_counter
    itens: list[PastelItem] = []
    nome = "Cliente"

    text_lower = text.lower()
    if "nome:" in text_lower:
        nome = text.split("nome:")[1].split(",")[0].strip()

    sabores_map = {
        "carne com queijo": SaborType.CARNE_QUEIJO,
        "carne e queijo": SaborType.CARNE_QUEIJO,
        "carne": SaborType.CARNE,
        "frango": SaborType.FRANGO,
        "queijo": SaborType.QUEIJO,
        "palmito": SaborType.PALMITO,
    }

    for sabor_name, sabor_type in sabores_map.items():
        if sabor_name in text_lower:
            qty = 1
            # Match patterns: "2 carne", "2x carne", "2 pastéis de carne"
            pattern = rf"(\d+)\s*(?:x\s*|past..s\s+de\s+)?{re.escape(sabor_name)}"
            match = re.search(pattern, text_lower)
            if match:
                qty = int(match.group(1))
            borda = BordaType.NORMAL
            if "catupiry" in text_lower:
                borda = BordaType.CATUPIRY
            elif "borda de queijo" in text_lower or "borda queijo" in text_lower:
                borda = BordaType.QUEIJO
            itens.append(PastelItem(sabor=sabor_type, quantidade=qty, borda=borda))

    if not itens:
        itens.append(PastelItem(sabor=SaborType.CARNE, quantidade=1))

    return nome, itens


class FilaExecutor(AgentExecutor):
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        global _queue_counter
        user_text = ""
        for part in context.message.parts:
            if hasattr(part, "text") and part.text:
                user_text = part.text
                break

        nome, itens = parse_order_text(user_text)
        order = create_order(nome, itens)
        _queue_counter += 1
        position = _queue_counter

        summary = order.to_summary()
        reply = (
            f"✅ Pedido recebido!\n"
            f"{summary}\n"
            f"📍 Posição na fila: {position}\n"
            f"⏳ Tempo estimado: ~{len(itens) * 3} minutos"
        )

        order.advance()  # PEDIDO -> FILA

        await event_queue.enqueue_event(Message(role=Role.agent, parts=[Part(text=reply)]))
