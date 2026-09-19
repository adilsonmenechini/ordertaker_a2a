"""Order data models for the pastel ordering system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    PEDIDO = "pedido"
    FILA = "fila"
    COZINHA = "cozinha"
    PREPARO = "preparo"
    ENTREGA = "entrega"
    CONCLUIDO = "concluido"


class BordaType(str, Enum):
    NORMAL = "normal"
    QUEIJO = "queijo"
    CATUPIRY = "catupiry"


class SaborType(str, Enum):
    CARNE = "carne"
    FRANGO = "frango"
    QUEIJO = "queijo"
    PALMITO = "palmito"
    CARNE_QUEIJO = "carne_com_queijo"


@dataclass
class PastelItem:
    sabor: SaborType
    quantidade: int = 1
    borda: BordaType = BordaType.NORMAL
    observacoes: str = ""


@dataclass
class Order:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    itens: list[PastelItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PEDIDO
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    timeline: dict[str, str] = field(default_factory=dict)
    cliente_nome: str = ""

    def advance(self) -> OrderStatus:
        sequence = list(OrderStatus)
        idx = sequence.index(self.status)
        if idx < len(sequence) - 1:
            self.status = sequence[idx + 1]
            self.timeline[self.status.value] = datetime.now().isoformat()
        return self.status

    def to_summary(self) -> str:
        itens_str = ", ".join(
            f"{i.quantidade}x pastel de {i.sabor.value} (borda {i.borda.value})" for i in self.itens
        )
        return f"Pedido #{self.id}: {itens_str} — Status: {self.status.value}"


# In-memory order store
_orders: dict[str, Order] = {}


def create_order(cliente_nome: str, itens: list[PastelItem]) -> Order:
    order = Order(cliente_nome=cliente_nome, itens=itens)
    order.timeline["pedido"] = datetime.now().isoformat()
    _orders[order.id] = order
    return order


def get_order(order_id: str) -> Order | None:
    return _orders.get(order_id)


def list_orders() -> list[Order]:
    return list(_orders.values())
