"""Test: state must be shared across agents.

When each A2A agent runs as a separate subprocess (run_all.py),
each has its own Python interpreter and memory space.
The in-memory order store in models/order.py is per-process,
so orders created by one agent are invisible to others.

This test reproduces the bug in-process by simulating separate
agent environments via subprocess isolation of the store.
"""
from __future__ import annotations
import json
import subprocess
import sys
import os
import tempfile

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _run_python(code: str) -> str:
    """Run Python code in an isolated process and return stdout."""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONPATH": PROJECT_ROOT},
        timeout=30,
    )
    return result.stdout.strip()


class TestMultiProcessState:
    """Verifies that orders are visible across agent boundaries."""

    def test_same_process_store_is_shared(self) -> None:
        """Within one process, the store is shared."""
        code = '''
import sys
sys.path.insert(0, ".")
from models.order import create_order, list_orders, PastelItem, SaborType
o1 = create_order("A", [PastelItem(sabor=SaborType.CARNE)])
o2 = create_order("B", [PastelItem(sabor=SaborType.FRANGO)])
print(json.dumps([{"id": o.id, "nome": o.cliente_nome} for o in list_orders()]))
'''
        output = _run_python(code)
        orders = json.loads(output)
        assert len(orders) == 2

    def test_isolated_process_has_empty_store(self) -> None:
        """A fresh process has an empty store (proves per-process state)."""
        code = '''
import sys
sys.path.insert(0, ".")
from models.order import list_orders
print(len(list_orders()))
'''
        output = _run_python(code)
        assert output.strip() == "0"

    def test_fila_create_not_visible_in_separate_process(self) -> None:
        """An order created in one process is NOT visible in another."""
        create_code = '''
import sys
sys.path.insert(0, ".")
from models.order import create_order, PastelItem, SaborType, get_order
o = create_order("João", [PastelItem(sabor=SaborType.CARNE)])
print(o.id)
'''
        order_id = _run_python(create_code)

        lookup_code = f'''
import sys
sys.path.insert(0, ".")
from models.order import get_order
result = get_order("{order_id}")
print("found" if result else "not_found")
'''
        output = _run_python(lookup_code)
        assert output.strip() == "not_found", (
            "Order created in one process should NOT be visible in another "
            "— this is the state isolation bug that needs fixing."
        )

    def test_full_pipeline_works_in_single_process(self) -> None:
        """The complete Fila→Cozinha→Preparo→Entrega flow in one process."""
        code = '''
import sys
sys.path.insert(0, ".")
from models.order import (
    create_order, list_orders, OrderStatus,
    PastelItem, SaborType, BordaType,
)
from server.executors.fila_executor import FilaExecutor
from server.executors.cozinha_executor import CozinhaExecutor
from server.executors.preparo_executor import PreparoExecutor
from server.executors.entrega_executor import EntregaExecutor
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role
import asyncio

async def run() -> None:
    # Fila creates order
    fila = FilaExecutor()
    eq = EventQueue()
    msg = Message(role=Role.USER, parts=[Part(text="2 pastéis de carne com borda de catupiry")])
    ctx = RequestContext(message=msg)
    await fila.execute(ctx, eq)

    order = list_orders()[0]
    assert order.status == OrderStatus.FILA

    # Cozinha processes
    cozinha = CozinhaExecutor()
    eq2 = EventQueue()
    ctx2 = RequestContext(message=Message(role=Role.USER, parts=[Part(text="preparar")]))
    await cozinha.execute(ctx2, eq2)
    assert order.status == OrderStatus.COZINHA

    # Preparo packages
    preparo = PreparoExecutor()
    eq3 = EventQueue()
    ctx3 = RequestContext(message=Message(role=Role.USER, parts=[Part(text="embalar")]))
    await preparo.execute(ctx3, eq3)
    assert order.status == OrderStatus.PREPARO

    # Entrega delivers
    entrega = EntregaExecutor()
    eq4 = EventQueue()
    ctx4 = RequestContext(message=Message(role=Role.USER, parts=[Part(text="entregar")]))
    await entrega.execute(ctx4, eq4)
    assert order.status == OrderStatus.ENTREGA

    return order.id

result = asyncio.run(run())
print(result)
'''
        output = _run_python(code)
        assert len(output.strip()) > 0, "Pipeline should complete in single process"
