"""Integration test: all agents share state when run in one process."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _run_python(code: str, timeout: int = 30) -> tuple[str, str]:
    """Run Python code in an isolated process and return (stdout, stderr)."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONPATH": PROJECT_ROOT},
        timeout=timeout,
    )
    return result.stdout.strip(), result.stderr.strip()


class TestRunAllIntegration:
    """Verifies shared state and agent lifecycle."""

    def test_process_isolation_proves_bug(self) -> None:
        """Separate processes do NOT share state (proves the bug)."""
        create_code = '''
import sys
sys.path.insert(0, ".")
from models.order import create_order, PastelItem, SaborType
o = create_order("Joao", [PastelItem(sabor=SaborType.CARNE)])
print(o.id)
'''
        order_id, _ = _run_python(create_code)

        lookup_code = f'''
import sys
sys.path.insert(0, ".")
from models.order import get_order
result = get_order("{order_id}")
print("found" if result else "not_found")
'''
        stdout, _ = _run_python(lookup_code)
        assert stdout.strip() == "not_found"

    def test_agents_share_state_in_threads(self) -> None:
        """When agents run in threads (like run_all.py), store is shared."""
        code = '''
import sys, os, json, threading, time
sys.path.insert(0, ".")
from models.order import (
    create_order, list_orders, get_order, OrderStatus,
    PastelItem, SaborType,
)

# Fila creates order in thread 1
def fila_worker() -> None:
    order = create_order("Joao", [PastelItem(sabor=SaborType.CARNE, quantidade=2)])
    order.advance()  # PEDIDO -> FILA

t = threading.Thread(target=fila_worker)
t.start()
t.join()

# Cozinha reads it in thread 2
results = {}
def cozinha_worker() -> None:
    orders = list_orders()
    results["count"] = len(orders)
    if orders:
        orders[0].advance()  # FILA -> COZINHA
        orders[0].advance()  # COZINHA -> PREPARO
        results["status"] = orders[0].status.value

t2 = threading.Thread(target=cozinha_worker)
t2.start()
t2.join()

# Entrega reads in thread 3
def entrega_worker() -> None:
    orders = list_orders()
    results["visible_to_entrega"] = len(orders)
    if orders:
        orders[0].advance()  # PREPARO -> ENTREGA
        orders[0].advance()  # ENTREGA -> CONCLUIDO
        results["status"] = orders[0].status.value

t3 = threading.Thread(target=entrega_worker)
t3.start()
t3.join()

print(json.dumps(results))
'''
        stdout, stderr = _run_python(code, timeout=30)
        if not stdout:
            pytest.fail(f"Pipeline output was empty.\nstderr: {stderr[-500:]}")
        data = json.loads(stdout)
        assert data["count"] == 1
        assert data["visible_to_entrega"] == 1
        assert data["status"] == "concluido"

    def test_multiple_orders_in_store(self) -> None:
        """Multiple orders are tracked in the shared store."""
        code = '''
import sys, os, json
sys.path.insert(0, ".")
from models.order import create_order, list_orders, PastelItem, SaborType
create_order("A", [PastelItem(sabor=SaborType.CARNE)])
create_order("B", [PastelItem(sabor=SaborType.FRANGO)])
create_order("C", [PastelItem(sabor=SaborType.QUEIJO)])
print(json.dumps(len(list_orders())))
'''
        stdout, _ = _run_python(code)
        assert stdout.strip() == "3"

