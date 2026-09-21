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
        # Filter out any non-JSON lines (e.g., warnings)
        lines = [l for l in output.split('\n') if l.strip().startswith('[')]
        json_line = lines[0] if lines else output
        orders = json.loads(json_line)
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
o = create_order("Joao", [PastelItem(sabor=SaborType.CARNE)])
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
        """The complete Fila->Cozinha->Preparo->Entrega flow in one process."""
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

async def run() -> str:
    # Fila creates order
    create_order("Joao", [PastelItem(sabor=SaborType.CARNE, quantidade=2)])
    order = list_orders()[0]
    assert order.status == OrderStatus.PEDIDO

    # Fila advances PEDIDO -> FILA
    order.advance()
    assert order.status == OrderStatus.FILA

    # Cozinha advances FILA -> COZINHA -> PREPARO
    cozinha = CozinhaExecutor()
    msg = Message(role=Role.ROLE_USER, parts=[Part(text="preparar")])
    ctx = RequestContext(call_context=None, request=None)
    ctx.__dict__["message"] = msg
    await cozinha.execute(ctx, EventQueue())
    assert order.status == OrderStatus.PREPARO

    # Preparo advances PREPARO -> ENTREGA
    preparo = PreparoExecutor()
    msg = Message(role=Role.ROLE_USER, parts=[Part(text="embalar")])
    ctx = RequestContext(call_context=None, request=None)
    ctx.__dict__["message"] = msg
    await preparo.execute(ctx, EventQueue())
    assert order.status == OrderStatus.ENTREGA

    # Entrega advances ENTREGA -> CONCLUIDO
    entrega = EntregaExecutor()
    msg = Message(role=Role.ROLE_USER, parts=[Part(text="entregar")])
    ctx = RequestContext(call_context=None, request=None)
    ctx.__dict__["message"] = msg
    await entrega.execute(ctx, EventQueue())
    assert order.status == OrderStatus.CONCLUIDO

    return order.id

result = asyncio.run(run())
print(result)
'''
        output = _run_python(code)
        lines = [l for l in output.split('\n') if l.strip() and not l.strip().startswith('RuntimeWarning')]
        json_line = lines[-1] if lines else output
        assert len(json_line.strip()) > 0, "Pipeline should complete in single process"