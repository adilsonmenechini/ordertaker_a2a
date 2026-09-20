# Fix A2A Flow: Shared Order Store with Explicit order_id Passing

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Solution Overview](#2-solution-overview)
3. [Changes Needed](#3-changes-needed)
   - [3.1 backend/models/order.py](#31-backendmodelsorderpy)
   - [3.2 backend/server/executors/*_executor.py](#32-backendserverexecutorsexecutorpy)
   - [3.3 backend/server/agent_server.py](#33-backendserveragent_serverpy)
   - [3.4 backend/client/sdk_client.py](#34-backendclientsdk_clientpy)
   - [3.5 backend/chat.py (optional)](#35-backendchatpy-optional)
   - [3.6 frontend/app/api/copilotkit/[...slug]/route.ts](#36-frontendappapicopilotkitslugroute.ts)
   - [3.7 frontend/components/OrderState.tsx](#37-frontendcomponentsOrderStatetsx)
   - [3.8 frontend/components/Chat.tsx](#38-frontendcomponentsChattsx)
   - [3.9 frontend/components/OrderDetails.tsx](#39-frontendcomponentsOrderDetailstsx)
   - [3.10 frontend/app/page.tsx](#310-frontendapppage.tsx)
4. [Testing Strategy](#4-testing-strategy)
5. [Migration Steps](#5-migration-steps)
6. [Rollback Plan](#6-rollback-plan)

---

## 1. Problem Statement

### 1.1 State Isolation in Multi-Process Deployment

The system runs 4 A2A agents (Fila, Cozinha, Preparo, Entrega) as **separate Python processes** via `run_all.py`:

```python
# backend/run_all.py — each agent is its own process
for agent in AGENTS:
    proc = subprocess.Popen(
        [sys.executable, "-m", "server.agent_server", agent],
        ...
    )
```

Each process imports `models.order` independently, creating a **separate copy** of the module-level `_orders` dictionary:

```python
# backend/models/order.py (current)
_orders: dict[str, Order] = {}  # <- EXISTS ONLY IN ONE PROCESS
```

**Consequences:**

- Fila agent creates an order in Process A's `_orders`.
- Cozinha agent calls `list_orders()` in Process B - sees an empty dict.
- Cozinha finds no active orders, sends "Nenhum pedido na cozinha no momento."
- The entire order pipeline silently fails.

This is confirmed by the Docker Compose setup where all agents share a container but run as separate Python processes (ports 9001-9004).

### 1.2 Latest-Order Guessing

Even if the store were shared, executors use fragile "last order" heuristics:

```python
# CozinhaExecutor.execute() - picks the LAST active order
orders = list_orders()
active = [o for o in orders if o.status in (OrderStatus.FILA, OrderStatus.COZINHA)]
order = active[-1]  # <- WHICH ORDER? What if multiple exist?
```

### 1.3 Frontend Keyword-Based State Detection

`Chat.tsx` detects order progress by scanning agent response text for keywords (`pedido`, `fila`, `cozinha`, `preparo`, `entrega`, `concluido`, etc.). This is unreliable because:

- Any agent message containing "pedido" (which is common) resets the step.
- Portuguese words appear in multiple contexts.
- If agent response text changes slightly, the entire timeline breaks silently.
- The step is determined by what the **agent says**, not by the actual **order state**.

### 1.4 No order_id in Orchestrator Tool Calls

The CopilotKit orchestrator in `route.ts` calls 4 tools sequentially (fila -> cozinha -> preparo -> entrega) but **never passes an order identifier** between them. Each tool call is independent with no way to reference the order created by the previous tool.

---

## 2. Solution Overview

### 2.1 Three Core Changes

| Change | Purpose | Files |
|--------|---------|-------|
| **Shared order store** | All agents see the same orders via SQLite | `models/order.py` |
| **Explicit order_id passing** | Each agent knows which order to work on | Executors, orchestrator, SDK client |
| **Backend-driven state** | UI reflects actual order status, not agent words | Frontend components, API route |

### 2.2 Architecture After Fix

```
Browser -> CopilotKit Chat
                |
                v
frontend/app/api/copilotkit/[...slug]/route.ts
  (orchestrator: generates order_id, passes to all tools,
   exposes GET /api/copilotkit/order/{order_id})
                |
                v
  Tool: agente_fila
    -> POST http://localhost:9001/a2a/jsonrpc
       message text: "[ORDER_ID: abc123] New order from Maria..."
    <- Reply contains [ORDER_ID: abc123] and order details
                |
                v
backend/models/order.py (SQLite store - shared across processes)
                |
                v
  Tool: agente_cozinha
    -> POST http://localhost:9002/a2a/jsonrpc
       message text: "[ORDER_ID: abc123] preparar"
    <- Reads order by ID (not list_orders[-1]), updates status
                |
                v
  (same pattern for preparo, entrega)
                |
                v
Frontend polls GET /api/copilotkit/order/{order_id}
for state updates (not keyword scanning)
```

### 2.3 Storage Choice: SQLite (Default)

**Why SQLite:**

- Zero new dependencies (built into Python 3.11 stdlib).
- Works across processes (file-based, ACID-compliant).
- Single-file database makes backup/migration trivial.
- No server to manage (unlike Redis).
- More than sufficient performance for a pastel ordering system.

**Upgrade path:** SQLite can be swapped for Redis/PostgreSQL later by changing only `models/order.py` - the interface (function signatures) stays the same.

### 2.4 order_id Convention

The order_id is embedded in A2A message text using a prefix:

```
"[ORDER_ID: abcd1234] actual message text here"
```

Receiving executors parse this prefix to determine which order to operate on. If no prefix is found, they fall back to `list_orders()` for backward compatibility during migration.

---

## 3. Changes Needed

### 3.1 `backend/models/order.py` - Shared Order Store

**Goal:** Replace in-memory `_orders` dict with a SQLite-backed store that works across processes. Keep the same public API so all callers continue to work.

#### 3.1.1 New imports to add (after existing imports, before dataclasses)

```python
import sqlite3
import os
import json

# Determine DB path - respects Docker volumes and local dev
DB_PATH = os.environ.get("ORDER_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "orders.db"))
DB_PATH = os.path.abspath(DB_PATH)


def _get_connection() -> sqlite3.Connection:
    """Open a connection to the shared order database."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db() -> None:
    """Create tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            cliente_nome TEXT NOT NULL DEFAULT '',
            itens TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'pedido',
            timestamp TEXT NOT NULL,
            timeline TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()

# Initialize on import
_init_db()
```

#### 3.1.2 Serialization helpers (add before `create_order`)

```python
def _row_to_order(row: sqlite3.Row) -> Order:
    """Convert a database row to an Order object."""
    return Order(
        id=row["id"],
        itens=json.loads(row["itens"]),
        status=OrderStatus(row["status"]),
        timestamp=row["timestamp"],
        timeline=json.loads(row["timeline"]),
        cliente_nome=row["cliente_nome"],
    )


def _serialize_items(itens: list[PastelItem]) -> str:
    return json.dumps([
        {"sabor": i.sabor.value, "quantidade": i.quantidade,
         "borda": i.borda.value, "observacoes": i.observacoes}
        for i in itens
    ])


def order_to_dict(order: Order) -> dict:
    """Serialize an Order to a plain dict for API responses."""
    return {
        "id": order.id,
        "cliente_nome": order.cliente_nome,
        "items": [
            {"sabor": i.sabor.value, "quantidade": i.quantidade,
             "borda": i.borda.value, "observacoes": i.observacoes}
            for i in order.itens
        ],
        "status": order.status.value,
        "timestamp": order.timestamp,
        "timeline": order.timeline,
    }
```

#### 3.1.3 Replace store functions (keep same signatures)

```python
def create_order(cliente_nome: str, itens: list[PastelItem]) -> Order:
    order = Order(cliente_nome=cliente_nome, itens=itens)
    order.timeline["pedido"] = datetime.now().isoformat()

    conn = _get_connection()
    conn.execute(
        "INSERT INTO orders (id, cliente_nome, itens, status, timestamp, timeline) VALUES (?, ?, ?, ?, ?, ?)",
        (order.id, order.cliente_nome, _serialize_items(order.itens),
         order.status.value, order.timestamp, json.dumps(order.timeline)),
    )
    conn.commit()
    conn.close()
    return order


def get_order(order_id: str) -> Order | None:
    conn = _get_connection()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_order(row)


def list_orders() -> list[Order]:
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM orders ORDER BY timestamp DESC").fetchall()
    conn.close()
    return [_row_to_order(row) for row in rows]


def update_order(order: Order) -> None:
    """Persist changes to an existing order."""
    conn = _get_connection()
    conn.execute(
        "UPDATE orders SET cliente_nome=?, itens=?, status=?, timestamp=?, timeline=?, updated_at=datetime('now') WHERE id=?",
        (order.cliente_nome, _serialize_items(order.itens), order.status.value,
         order.timestamp, json.dumps(order.timeline), order.id),
    )
    conn.commit()
    conn.close()


def update_order_status(order_id: str, new_status: OrderStatus) -> Order | None:
    """Atomically advance and persist an order's status."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        conn.close()
        return None
    order = _row_to_order(row)
    order.advance()
    conn.execute(
        "UPDATE orders SET status=?, timeline=?, updated_at=datetime('now') WHERE id=?",
        (order.status.value, json.dumps(order.timeline), order.id),
    )
    conn.commit()
    conn.close()
    return order
```

#### 3.1.4 Backward compatibility

- `create_order`, `get_order`, `list_orders` keep the **exact same signatures**.
- All executor tests continue to work (same function signatures).
- The `_orders` dict is **removed**. Tests that use it directly must be updated.

---

### 3.2 `backend/server/executors/*_executor.py` - Accept and Return order_id

#### 3.2.1 Add shared helper to `backend/server/executors/__init__.py`

```python
"""Shared utilities for A2A agent executors."""
import re
from models.order import extract_order_id  # will be added to models/order.py

ORDER_ID_PATTERN = re.compile(r"\[ORDER_ID:\s*([a-zA-Z0-9]+)\]")


def extract_order_id(text: str) -> str | None:
    """Extract order_id from message text if present."""
    match = ORDER_ID_PATTERN.search(text)
    return match.group(1) if match else None
```

Wait - `extract_order_id` should live in `models/order.py` so it can be imported from both backend and tests. Let me correct:

#### 3.2.2 Add to `backend/models/order.py` (after the store functions)

```python
import re

ORDER_ID_PATTERN = re.compile(r"\[ORDER_ID:\s*([a-zA-Z0-9]+)\]")


def embed_order_id(text: str, order_id: str) -> str:
    """Prepend order_id marker to a message text."""
    return f"[ORDER_ID: {order_id}] {text}"


def extract_order_id(text: str) -> str | None:
    """Extract order_id from message text."""
    match = ORDER_ID_PATTERN.search(text)
    return match.group(1) if match else None
```

#### 3.2.3 `backend/server/executors/fila_executor.py`

**Full file replacement** (simplest approach):

Key changes:
- Remove `_queue_counter` global.
- After creating order, embed order_id in reply: `[ORDER_ID: {order.id}]`.
- Check incoming message for `[ORDER_ID: ...]` prefix - if present and order exists in PEDIDO/FILA status, report status instead of creating new order.

```python
"""Fila agent - receives order, places in queue, returns position with order_id."""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role

from models.order import (
    BordaType, PastelItem, SaborType, create_order, get_order,
    OrderStatus, extract_order_id,
)


def parse_order_text(text: str) -> tuple[str, list[PastelItem]]:
    """Simple deterministic parser for order text."""
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
        user_text = ""
        for part in context.message.parts:
            if hasattr(part, "text") and part.text:
                user_text = part.text
                break

        # Check if this references an existing order via order_id
        existing_order_id = extract_order_id(user_text)
        if existing_order_id:
            existing = get_order(existing_order_id)
            if existing and existing.status in (OrderStatus.PEDIDO, OrderStatus.FILA):
                summary = existing.to_summary()
                reply = f"[ORDER_ID: {existing.id}] {summary} - Status: {existing.status.value}"
                await event_queue.enqueue_event(
                    Message(role=Role.ROLE_AGENT, parts=[Part(text=reply)]),
                )
                return

        nome, itens = parse_order_text(user_text)
        order = create_order(nome, itens)
        order.advance()  # PEDIDO -> FILA

        summary = order.to_summary()
        reply = (
            f"[ORDER_ID: {order.id}] "
            f"Pedido recebido!\n"
            f"{summary}\n"
            f"Posicao na fila: 1\n"
            f"Tempo estimado: ~{len(itens) * 3} minutos"
        )

        await event_queue.enqueue_event(
            Message(role=Role.ROLE_AGENT, parts=[Part(text=reply)]),
        )
```

#### 3.2.4 `backend/server/executors/cozinha_executor.py`

Key changes:
- Parse `order_id` from incoming message.
- Use `get_order(order_id)` instead of `list_orders()[-1]`.
- After each status change, call `update_order(order)` to persist to shared store.
- Embed `order_id` in final reply.

```python
"""Cozinha agent - streaming preparation progress via SSE."""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role

from models.order import OrderStatus, get_order, update_order, list_orders, extract_order_id


class CozinhaExecutor(AgentExecutor):
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = ""
        for part in context.message.parts:
            if hasattr(part, "text") and part.text:
                user_text = part.text
                break

        # Try to find order by order_id
        order = None
        order_id = extract_order_id(user_text)
        if order_id:
            order = get_order(order_id)
            if order and order.status not in (OrderStatus.FILA, OrderStatus.COZINHA):
                order = None

        # Fallback: find active order (backward compat during migration)
        if order is None:
            orders = list_orders()
            active = [o for o in orders if o.status in (OrderStatus.FILA, OrderStatus.COZINHA)]
            if not active:
                msg = "Nenhum pedido na cozinha no momento."
                await event_queue.enqueue_event(
                    Message(role=Role.ROLE_AGENT, parts=[Part(text=msg)]),
                )
                return
            order = active[-1]
            order_id = order.id

        order.advance()  # FILA -> COZINHA
        update_order(order)  # PERSIST

        steps = [
            "Aquecendo o oleo...",
            "Massa sendo aberta...",
            "Recheio sendo preparado...",
            "Montando o pastel...",
            "Fritando... golden & crispy!",
            "Cozinha finalizou o pedido!",
        ]

        for step in steps:
            await event_queue.enqueue_event(
                Message(role=Role.ROLE_AGENT, parts=[Part(text=step)]),
            )
            await asyncio.sleep(1.5)

        order.advance()  # COZINHA -> PREPARO
        update_order(order)  # PERSIST

        await event_queue.enqueue_event(
            Message(
                role=Role.ROLE_AGENT,
                parts=[Part(text=f"[ORDER_ID: {order_id}] Pedido {order_id} saiu da cozinha e esta no preparo.")],
            ),
        )
```

#### 3.2.5 `backend/server/executors/preparo_executor.py`

Same pattern (parse order_id, get_order, update_order, embed in reply):

```python
"""Preparo agent - long-running task with progress polling."""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role

from models.order import OrderStatus, get_order, update_order, list_orders, extract_order_id


class PreparoExecutor(AgentExecutor):
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = ""
        for part in context.message.parts:
            if hasattr(part, "text") and part.text:
                user_text = part.text
                break

        order = None
        order_id = extract_order_id(user_text)
        if order_id:
            order = get_order(order_id)
            if order and order.status != OrderStatus.PREPARO:
                order = None

        if order is None:
            orders = list_orders()
            active = [o for o in orders if o.status == OrderStatus.PREPARO]
            if not active:
                await event_queue.enqueue_event(
                    Message(role=Role.ROLE_AGENT, parts=[Part(text="Nenhum pedido para preparar.")]),
                )
                return
            order = active[-1]
            order_id = order.id

        steps = [
            "Enfatizando a embalagem...",
            "Colocando etiqueta do pedido...",
            "Pronto para entrega!",
        ]

        for msg in steps:
            await event_queue.enqueue_event(
                Message(role=Role.ROLE_AGENT, parts=[Part(text=msg)]),
            )
            await asyncio.sleep(2)

        order.advance()  # PREPARO -> ENTREGA
        update_order(order)

        await event_queue.enqueue_event(
            Message(
                role=Role.ROLE_AGENT,
                parts=[Part(text=f"[ORDER_ID: {order_id}] Pedido {order_id} saiu para entrega!")],
            ),
        )
```

#### 3.2.6 `backend/server/executors/entrega_executor.py`

Same pattern:

```python
"""Entrega agent - confirms delivery."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role

from models.order import OrderStatus, get_order, update_order, list_orders, extract_order_id


class EntregaExecutor(AgentExecutor):
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = ""
        for part in context.message.parts:
            if hasattr(part, "text") and part.text:
                user_text = part.text
                break

        order = None
        order_id = extract_order_id(user_text)
        if order_id:
            order = get_order(order_id)

        if order is None:
            orders = list_orders()
            active = [o for o in orders if o.status == OrderStatus.ENTREGA]
            if not active:
                await event_queue.enqueue_event(
                    Message(role=Role.ROLE_AGENT, parts=[Part(text="Nenhum pedido para entregar.")]),
                )
                return
            order = active[-1]
            order_id = order.id

        order.advance()  # ENTREGA -> CONCLUIDO
        update_order(order)

        await event_queue.enqueue_event(
            Message(
                role=Role.ROLE_AGENT,
                parts=[
                    Part(
                        text=(
                            f"[ORDER_ID: {order_id}] Pedido {order_id} entregue com sucesso!\n"
                            f"Cliente: {order.cliente_nome}\n"
                            f"Status: CONCLUIDO\n"
                            f"Obrigado pela preferência!"
                        )
                    )
                ],
            ),
        )
```

#### 3.2.7 `backend/server/executors/__init__.py`

No changes needed (empty file).

---

### 3.3 `backend/server/agent_server.py` - Minor additions

Add a health endpoint inside `create_app()`:

```python
from fastapi import APIRouter

# Inside create_app(), before `return app`:
health_router = APIRouter()

@health_router.get("/health")
def health_check():
    return {"status": "ok", "agent": config["name"]}

app.include_router(health_router)
```

Also ensure `models/order.py` `_init_db()` creates the parent directory:
```python
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
```

---

### 3.4 `backend/client/sdk_client.py` - Helpers for order_id

#### 3.4.1 Add to existing file (after `A2A_HEADERS` constant, before functions)

```python
import re

ORDER_ID_PATTERN = re.compile(r"\[ORDER_ID:\s*([a-zA-Z0-9]+)\]")


def embed_order_id(text: str, order_id: str) -> str:
    """Prepend order_id marker to a message text."""
    return f"[ORDER_ID: {order_id}] {text}"


def extract_order_id(text: str) -> str | None:
    """Extract order_id from message text."""
    match = ORDER_ID_PATTERN.search(text)
    return match.group(1) if match else None
```

#### 3.4.2 Modify `send_message` to accept optional order_id

```python
async def send_message(
    client: httpx.AsyncClient,
    jsonrpc_url: str,
    text: str,
    return_immediately: bool = False,
    order_id: str | None = None,
) -> dict:
    if order_id is not None:
        text = f"[ORDER_ID: {order_id}] {text}"

    params: dict[str, Any] = {
        "message": {
            "role": 1,
            "message_id": str(uuid.uuid4()),
            "parts": [{"text": text}],
        },
    }
    if return_immediately:
        params["configuration"] = {"return_immediately": True}
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "SendMessage",
        "params": params,
    }
    resp = await client.post(jsonrpc_url, json=payload, headers=A2A_HEADERS, timeout=30)
    body = resp.json()
    if "error" in body:
        raise RuntimeError(f"JSON-RPC error: {body['error']}")
    return body.get("result", {})
```

#### 3.4.3 Add a pipeline helper

```python
async def run_order_pipeline(
    client: httpx.AsyncClient,
    user_message: str,
    agent_base_urls: dict[str, str] | None = None,
    on_progress: Callable[[str], Any] | None = None,
) -> dict:
    """Run full pipeline: fila -> cozinha -> preparo -> entrega. Returns order_id and final reply."""
    urls = agent_base_urls or AGENT_URLS

    # Step 1: Fila creates order
    result = await send_message(client, f"{urls['fila']}/a2a/jsonrpc", user_message)
    reply = extract_reply_text(result)
    order_id = extract_order_id(reply)
    if not order_id:
        raise RuntimeError("No order_id returned by fila agent")
    if on_progress:
        on_progress(f"Pedido {order_id} recebido na fila")

    # Step 2: Cozinha
    await send_message(client, f"{urls['cozinha']}/a2a/jsonrpc", "preparar", order_id=order_id)
    if on_progress:
        on_progress(f"Pedido {order_id} sendo preparado")

    # Step 3: Preparo (with polling)
    result = await send_message(
        client, f"{urls['preparo']}/a2a/jsonrpc", "embalar",
        return_immediately=True, order_id=order_id,
    )
    task_id = get_task_id(result)
    if task_id:
        reply = await poll_task(
            client, f"{urls['preparo']}/a2a/jsonrpc", task_id,
            on_progress=on_progress,
        )

    # Step 4: Entrega
    result = await send_message(
        client, f"{urls['entrega']}/a2a/jsonrpc", "entregar", order_id=order_id,
    )
    return {"order_id": order_id, "final_reply": extract_reply_text(result)}
```

---

### 3.5 `backend/chat.py` (optional)

Replace the sequential agent calls with a single `run_order_pipeline` call:

```python
# At top of file, add:
from client.sdk_client import run_order_pipeline

# Inside the while loop, replace sequential calls with:
result = await run_order_pipeline(
    client, user_input, agent_base_urls=AGENT_URLS, on_progress=print,
)
print(f"Resultado: {result['final_reply']}")
print(f"Order ID: {result['order_id']}")
```

---

### 3.6 `frontend/app/api/copilotkit/[...slug]/route.ts` - Orchestrator

#### 3.6.1 Add types and order_id utilities at top of file

```typescript
// Add after A2A_HEADERS constant:

const ORDER_ID_PATTERN = /\[ORDER_ID:\s*([a-zA-Z0-9]+)\]/;

function extractOrderIdFromText(text: string): string | null {
  const match = text.match(ORDER_ID_PATTERN);
  return match ? match[1] : null;
}

interface OrderStateData {
  id: string;
  items: Array<{ sabor: string; quantidade: number; borda: string }>;
  status: string;
  cliente_nome: string;
  timestamp: string;
  timeline: Record<string, string>;
}

// Server-side cache (in-memory, resets on restart - acceptable for MVP)
const orderCache = new Map<string, OrderStateData>();
```

#### 3.6.2 Update `callA2AAgent` to accept and embed order_id

```typescript
async function callA2AAgent(
  agent: string,
  text: string,
  orderId?: string,
): Promise<string> {
  const baseUrl = getAgentUrl(agent);
  const jsonrpcUrl = `${baseUrl}/a2a/jsonrpc`;

  const messageText = orderId ? `[ORDER_ID: ${orderId}] ${text}` : text;

  const payload = {
    jsonrpc: "2.0",
    id: crypto.randomUUID(),
    method: "SendMessage",
    params: {
      message: {
        role: 1,
        message_id: crypto.randomUUID(),
        parts: [{ text: messageText }],
      },
    },
  };

  console.log(`[A2A] Calling ${agent} at ${jsonrpcUrl}${orderId ? ` (order: ${orderId})` : ""}`);
  const resp = await fetch(jsonrpcUrl, {
    method: "POST",
    headers: A2A_HEADERS,
    body: JSON.stringify(payload),
  });
  const body = await resp.json();
  if (body.error) throw new Error(`A2A ${agent} error: ${JSON.stringify(body.error)}`);
  const result = body.result || {};
  return extractReplyText(result);
}
```

#### 3.6.3 Update each tool to accept order_id parameter

**`filaTool`** - Generates order_id on first call:

```typescript
const filaTool = defineTool({
  name: "agente_fila",
  description: "Recebe o pedido do cliente e o posiciona na fila. Gera um order_id. Use PRIMEIRO.",
  parameters: z.object({
    pedido: z.string().describe("Descricao do pedido"),
    nome_cliente: z.string().describe("Nome do cliente"),
  }),
  execute: async ({ pedido, nome_cliente }) => {
    const text = `Novo pedido de ${nome_cliente}: ${pedido}`;
    const reply = await callA2AAgent("fila", text);
    const extractedId = extractOrderIdFromText(reply);

    // Cache order state for frontend polling
    if (extractedId) {
      orderCache.set(extractedId, {
        id: extractedId,
        items: [],
        status: "fila",
        cliente_nome: nome_cliente,
        timestamp: new Date().toISOString(),
        timeline: {},
      });
    }

    return { resultado_fila: reply, order_id: extractedId || "" };
  },
});
```

**`cozinhaTool`** - Receives order_id from fila:

```typescript
const cozinhaTool = defineTool({
  name: "agente_cozinha",
  description: "Prepara o(s) pastel(is). Recebe order_id do agente_fila.",
  parameters: z.object({
    pedido: z.string().describe("Descricao do pedido"),
    nome_cliente: z.string().describe("Nome do cliente"),
    order_id: z.string().describe("ID do pedido recebido da fila"),
  }),
  execute: async ({ pedido, nome_cliente, order_id }) => {
    const text = `Preparar pedido de ${nome_cliente}: ${pedido}`;
    const reply = await callA2AAgent("cozinha", text, order_id);
    if (order_id) {
      const cached = orderCache.get(order_id);
      if (cached) cached.status = "cozinha";
    }
    return { resultado_cozinha: reply };
  },
});
```

**`preparoTool`** - Receives order_id from cozinha:

```typescript
const preparoTool = defineTool({
  name: "agente_preparo",
  description: "Embala o(s) pastel(is). Recebe order_id do agente_cozinha.",
  parameters: z.object({
    pedido: z.string().describe("Descricao do pedido preparado"),
    nome_cliente: z.string().describe("Nome do cliente"),
    order_id: z.string().describe("ID do pedido"),
  }),
  execute: async ({ pedido, nome_cliente, order_id }) => {
    const text = `Embalar pedido de ${nome_cliente}: ${pedido}`;
    const reply = await callA2AAgent("preparo", text, order_id);
    if (order_id) {
      const cached = orderCache.get(order_id);
      if (cached) cached.status = "preparo";
    }
    return { resultado_preparo: reply };
  },
});
```

**`entregaTool`** - Receives order_id from preparo, final status update:

```typescript
const entregaTool = defineTool({
  name: "agente_entrega",
  description: "Entrega o pedido ao cliente. Recebe order_id do agente_preparo.",
  parameters: z.object({
    pedido: z.string().describe("Descricao do pedido embalado"),
    nome_cliente: z.string().describe("Nome do cliente"),
    order_id: z.string().describe("ID do pedido"),
  }),
  execute: async ({ pedido, nome_cliente, order_id }) => {
    const text = `Entregar pedido de ${nome_cliente}: ${pedido}`;
    const reply = await callA2AAgent("entrega", text, order_id);
    if (order_id) {
      const cached = orderCache.get(order_id);
      if (cached) {
        cached.status = "entrega";
        // Optional: remove from cache after delivery confirmation
        // orderCache.delete(order_id);
      }
    }
    return { resultado_entrega: reply };
  },
});
```

#### 3.6.4 Update SYSTEM_PROMPT to mention order_id

```typescript
const SYSTEM_PROMPT = `Voce e o atendente virtual da Pastelaria "Sabor da Terra".
Gerencia pedidos de pastel usando agentes especializados.

IMPORTANTE - order_id:
- Ao receber um pedido, gere um order_id (UUID) e USE-O em TODAS as chamadas subsequentes.
- Passe o order_id para agente_cozinha, agente_preparo e agente_entrega como parametro order_id.
- O order_id garante que cada agente trabalha no pedido correto.

IMPRESCINDIVEL: Logo no inicio da conversa, SEMPRE chame a tool 'mostrar_cardapio'...

FLUXO DO PEDIDO:
1. agente_fila - Recebe o pedido e gera order_id (PRIMEIRO)
2. agente_cozinha - Prepara o pastel (com streaming) - passe order_id
3. agente_preparo - Embala o pedido - passe order_id
4. agente_entrega - Entrega ao cliente - passe order_id

[... rest unchanged ...]`;
```

#### 3.6.5 Add order status endpoint

Add a handler for querying cached order state:

```typescript
async function handleRequest(request: NextRequest): Promise<Response> {
  try {
    console.log("[CopilotKit]", request.method, request.nextUrl.pathname);

    // GET /api/copilotkit/order/status?order_id=abc123
    if (request.method === "GET" && request.nextUrl.pathname.endsWith("/order/status")) {
      const orderId = request.nextUrl.searchParams.get("order_id");
      if (!orderId) {
        return NextResponse.json({ error: "order_id required" }, { status: 400 });
      }
      const cached = orderCache.get(orderId);
      if (!cached) {
        return NextResponse.json({ error: "order not found" }, { status: 404 });
      }
      return NextResponse.json(cached);
    }

    const handler = await getHandler();
    const response = await handler(request);
    for (const [k, v] of Object.entries(corsHeaders)) {
      response.headers.set(k, v);
    }
    return response;
  } catch (err) {
    console.error("[CopilotKit] Request error:", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal error" },
      { status: 500 },
    );
  }
}
```

---

### 3.7 `frontend/components/OrderState.tsx` - Backend-Driven State

Add `order_id` field and polling function. Export `OrderState` interface so other components can use it.

Key additions:
- `order_id: string` field in `OrderState` interface.
- `setOrderId(id: string)` function.
- `pollOrderStatus(orderId: string)` async function that calls the new status endpoint.
- `STATUS_TO_STEP` mapping for converting backend status strings to timeline step indices.

---

### 3.8 `frontend/components/Chat.tsx` - Remove Keyword Detection

**Remove entirely:**
- `STEP_KEYWORDS` constant (lines 10-22)
- `detectStep` function (lines 24-30)
- The `useEffect` that scans messages (lines 53-76)

**Add:**
- Extract order_id from agent responses (first tool call returns it).
- Start polling `pollOrderStatus(orderId)` when order_id is set.

---

### 3.9 `frontend/components/OrderDetails.tsx` - Show order_id

Add display of `order_id` and backend `status` badge in the summary section. The component already accepts `OrderState` as props; the interface change in 3.7 automatically makes `order_id` and updated `status` available.

---

### 3.10 `frontend/app/page.tsx`

No changes needed. It already uses `useOrderState()` correctly.

---

## 4. Testing Strategy

### 4.1 Update `backend/tests/test_models.py`

**Remove** the `_orders.clear()` pattern in `setup_method`. Replace with direct SQLite cleanup:

```python
def setup_method(self):
    """Clear store before each test."""
    import sqlite3
    from models.order import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM orders")
    conn.commit()
    conn.close()
```

**Update all tests** to use the public API:

```python
class TestOrderStore:
    def setup_method(self):
        import sqlite3
        from models.order import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM orders")
        conn.commit()
        conn.close()

    def test_create_order_adds_to_store(self):
        item = PastelItem(sabor=SaborType.CARNE)
        order = create_order("Teste", [item])
        assert order.cliente_nome == "Teste"
        assert order.id is not None
        assert len(order.id) == 8
        retrieved = get_order(order.id)
        assert retrieved is not None
        assert retrieved.cliente_nome == "Teste"
        assert order.id in [o.id for o in list_orders()]

    def test_update_order_persists(self):
        order = create_order("Teste", [PastelItem(sabor=SaborType.CARNE)])
        order.advance()
        update_order(order)
        retrieved = get_order(order.id)
        assert retrieved.status == OrderStatus.FILA

    def test_update_order_status(self):
        order = create_order("Teste", [PastelItem(sabor=SaborType.CARNE)])
        updated = update_order_status(order.id, OrderStatus.COZINHA)
        assert updated is not None
        assert updated.status == OrderStatus.COZINHA
        retrieved = get_order(order.id)
        assert retrieved.status == OrderStatus.COZINHA

    def test_order_to_dict(self):
        order = create_order("Maria", [PastelItem(sabor=SaborType.FRANGO, quantidade=2)])
        d = order_to_dict(order)
        assert d["id"] == order.id
        assert d["status"] == "pedido"
        assert len(d["items"]) == 1
        assert d["items"][0]["sabor"] == "frango"

    def test_get_order_not_found(self):
        assert get_order("nonexistent") is None

    def test_delete_order(self):
        order = create_order("Teste", [PastelItem(sabor=SaborType.CARNE)])
        from models.order import delete_order
        assert delete_order(order.id) is True
        assert get_order(order.id) is None
```

### 4.2 Update `backend/tests/test_executors.py`

**Replace all `_orders.clear()` calls** with SQLite cleanup in setup:

```python
def setup_method(self):
    import sqlite3
    from models.order import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM orders")
    conn.commit()
    conn.close()
```

**Update executor tests** to use order_id pattern:

```python
class TestCozinhaExecutor:
    def setup_method(self):
        import sqlite3
        from models.order import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM orders")
        conn.commit()
        conn.close()

    @pytest.mark.asyncio
    async def test_cozinha_processes_by_order_id(self):
        from models.order import OrderStatus, PastelItem, SaborType, create_order, get_order, update_order
        from server.executors.cozinha_executor import CozinhaExecutor

        order = create_order("Teste", [PastelItem(sabor=SaborType.CARNE)])
        order.advance()  # PEDIDO -> FILA
        update_order(order)
        assert order.status == OrderStatus.FILA

        executor = CozinhaExecutor()
        context = MagicMock()
        context.message = Message(
            role=Role.ROLE_USER,
            parts=[Part(text=f"[ORDER_ID: {order.id}] preparar")],
        )
        event_queue = AsyncMock()

        await executor.execute(context, event_queue)

        updated = get_order(order.id)
        assert updated.status == OrderStatus.PREPARO
        # Verify reply contains order_id
        enqueued = event_queue.enqueue_event.call_args[0][0]
        assert any("[ORDER_ID:" in p.text for p in enqueued.parts if p.text)

    @pytest.mark.asyncio
    async def test_cozinha_falls_back_to_list_orders(self):
        """Without order_id, falls back to list_orders[-1]."""
        from models.order import OrderStatus, PastelItem, SaborType, create_order
        from server.executors.cozinha_executor import CozinhaExecutor

        create_order("Teste", [PastelItem(sabor=SaborType.CARNE)])
        # Don't advance to FILA - simulates no shared store, only in-memory
        # (but since we use SQLite, it WILL be in the store)

        executor = CozinhaExecutor()
        context = MagicMock()
        context.message = Message(
            role=Role.ROLE_USER,
            parts=[Part(text="preparar")],  # No order_id prefix
        )
        event_queue = AsyncMock()

        await executor.execute(context, event_queue)
        # Should have sent at least one message
        assert event_queue.enqueue_event.call_count >= 1
```

### 4.3 New test file: `backend/tests/test_order_id.py`

```python
"""Tests for order_id embedding/extraction."""

import re

import pytest


class TestEmbedOrderId:
    def test_embed_order_id(self):
        from models.order import embed_order_id
        assert embed_order_id("preparar", "abc123") == "[ORDER_ID: abc123] preparar"

    def test_embed_order_id_empty(self):
        from models.order import embed_order_id
        result = embed_order_id("test", "")
        assert result.startswith("[ORDER_ID: ]")


class TestExtractOrderId:
    def test_extract_from_prefixed_text(self):
        from models.order import extract_order_id
        assert extract_order_id("[ORDER_ID: abc123] Hello") == "abc123"

    def test_extract_from_complex_reply(self):
        from models.order import extract_order_id
        text = "[ORDER_ID: xyz789] Pedido recebido!\nDetalhes..."
        assert extract_order_id(text) == "xyz789"

    def test_no_order_id_returns_none(self):
        from models.order import extract_order_id
        assert extract_order_id("Sem order id aqui") is None

    def test_multiple_order_ids_returns_first(self):
        from models.order import extract_order_id
        text = "[ORDER_ID: first] ... [ORDER_ID: second] ..."
        assert extract_order_id(text) == "first"

    def test_order_id_with_spaces(self):
        from models.order import extract_order_id
        assert extract_order_id("[ORDER_ID: my order 123]") == "my order 123"


class TestOrderIdPattern:
    """Verify regex pattern consistency."""
    def test_pattern_matches_fila_format(self):
        from models.order import ORDER_ID_PATTERN
        assert ORDER_ID_PATTERN.match("[ORDER_ID: abcd1234]") is not None

    def test_pattern_does_not_match_bare_id(self):
        from models.order import ORDER_ID_PATTERN
        assert ORDER_ID_PATTERN.match("abcd1234") is None
```

### 4.4 Update `backend/tests/test_sdk_client.py`

Add tests for `embed_order_id` and `extract_order_id` from `sdk_client.py`:

```python
from client.sdk_client import extract_reply_text, get_task_id, embed_order_id, extract_order_id


class TestEmbedOrderId:
    def test_embed_order_id(self):
        assert embed_order_id("preparar", "abc123") == "[ORDER_ID: abc123] preparar"


class TestExtractOrderId:
    def test_extract_from_prefixed_text(self):
        assert extract_order_id("[ORDER_ID: abc123] Hello") == "abc123"

    def test_no_order_id(self):
        assert extract_order_id("Hello world") is None


# Existing TestExtractReplyText and TestGetTaskId remain unchanged
```

### 4.5 New integration test: `backend/tests/test_pipeline.py`

```python
"""Integration test: full order pipeline across processes."""

import asyncio
import re
import sys
import os

import pytest
import httpx

# Ensure backend path is available
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestOrderPipeline:
    @pytest.mark.asyncio
    async def test_fila_returns_order_id(self):
        """Fila agent must embed order_id in response."""
        async with httpx.AsyncClient() as client:
            result = await client.post(
                "http://localhost:9001/a2a/jsonrpc",
                json={
                    "jsonrpc": "2.0",
                    "id": "test-1",
                    "method": "SendMessage",
                    "params": {
                        "message": {
                            "role": 1,
                            "message_id": "msg-1",
                            "parts": [{"text": "2 pastéis de carne"}],
                        }
                    },
                },
            )
            body = result.json()
            reply_text = " ".join(
                p.get("text", "")
                for p in body.get("result", {}).get("task", {}).get("status", {}).get("message", {}).get("parts", [])
            )
            assert re.search(r"\[ORDER_ID:\s*\w+\]", reply_text), f"No order_id in: {reply_text}"

    @pytest.mark.asyncio
    async def test_cozinha_finds_order_by_id(self):
        """Cozinha must process order when given order_id."""
        async with httpx.AsyncClient() as client:
            # Create order via fila
            r1 = await client.post(
                "http://localhost:9001/a2a/jsonrpc",
                json={
                    "jsonrpc": "2.0", "id": "t1", "method": "SendMessage",
                    "params": {"message": {"role": 1, "message_id": "m1",
                        "parts": [{"text": "1 pastel de frango"}]}},
                },
            )
            reply1 = " ".join(p.get("text", "") for p in r1.json().get("result", {}).get("task", {}).get("status", {}).get("message", {}).get("parts", []))
            order_id_match = re.search(r"\[ORDER_ID:\s*(\w+)\]", reply1)
            assert order_id_match, "No order_id from fila"
            order_id = order_id_match.group(1)

            # Process via cozinha with order_id
            r2 = await client.post(
                "http://localhost:9002/a2a/jsonrpc",
                json={
                    "jsonrpc": "2.0", "id": "t2", "method": "SendMessage",
                    "params": {"message": {"role": 1, "message_id": "m2",
                        "parts": [{"text": f"[ORDER_ID: {order_id}] preparar"}]}},
                },
            )
            assert r2.status_code == 200
```

### 4.6 Frontend Tests

#### 4.6.1 Update `__tests__/OrderState.test.tsx`

Add tests for `order_id`, `setOrderId`, and `pollOrderStatus`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { OrderStateProvider, useOrderState, ORDER_STEPS } from "@/components/OrderState";

function TestConsumer() {
  const { order, currentStep, setOrder, setCurrentStep, setOrderId, pollOrderStatus } = useOrderState();
  return (
    <div>
      <span data-testid="status">{order.status}</span>
      <span data-testid="step">{currentStep}</span>
      <span data-testid="items-count">{order.items.length}</span>
      <span data-testid="order-id">{order.order_id}</span>
      <button onClick={() => setCurrentStep(2)}>Go to cozinha</button>
      <button
        onClick={() =>
          setOrder({
            order_id: "test-123",
            items: [{ sabor: "carne", quantidade: 2, borda: "catupiry" }],
            status: "pedido",
            cliente: "Maria",
          })
        }
      >
        Set order
      </button>
      <button onClick={() => setOrderId("abc-456")}>Set order ID</button>
      <button onClick={() => pollOrderStatus("test")}>Poll</button>
    </div>
  );
}

describe("OrderState", () => {
  it("provides default state with empty order_id", () => {
    render(
      <OrderStateProvider><TestConsumer /></OrderStateProvider>,
    );
    expect(screen.getByTestId("order-id").textContent).toBe("");
    expect(screen.getByTestId("status").textContent).toBe("aguardando");
    expect(screen.getByTestId("step").textContent).toBe("-1");
  });

  it("sets order_id via setOrderId", () => {
    render(
      <OrderStateProvider><TestConsumer /></OrderStateProvider>,
    );
    fireEvent.click(screen.getByText("Set order ID"));
    expect(screen.getByTestId("order-id").textContent).toBe("abc-456");
  });

  it("updates order via setOrder (with order_id)", () => {
    render(
      <OrderStateProvider><TestConsumer /></OrderStateProvider>,
    );
    fireEvent.click(screen.getByText("Set order"));
    expect(screen.getByTestId("order-id").textContent).toBe("test-123");
    expect(screen.getByTestId("items-count").textContent).toBe("1");
  });

  it("throws when used outside provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    function BadConsumer() { useOrderState(); return null; }
    expect(() => render(<BadConsumer />)).toThrow("useOrderState must be used within OrderStateProvider");
    spy.mockRestore();
  });
});
```

#### 4.6.2 New test file: `frontend/__tests__/ChatKeywordRegression.test.tsx`

Regression test to ensure keyword detection is removed:

```typescript
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

describe("Chat.tsx keyword detection regression", () => {
  it("does NOT contain STEP_KEYWORDS", () => {
    const chatPath = resolve(__dirname, "../components/Chat.tsx");
    const source = readFileSync(chatPath, "utf-8");
    expect(source).not.toContain("STEP_KEYWORDS");
    expect(source).not.toContain("detectStep");
  });

  it("DOES contain pollOrderStatus", () => {
    const chatPath = resolve(__dirname, "../components/Chat.tsx");
    const source = readFileSync(chatPath, "utf-8");
    expect(source).toContain("pollOrderStatus");
  });
});
```

#### 4.6.3 Update `__tests__/OrderDetails.test.tsx`

Add tests for `order_id` and `status` display:

```typescript
it("renders order_id when present", () => {
  render(<OrderDetails order={orderWithItems} />);
  expect(screen.getByText("abcd1234")).toBeInTheDocument();
});

it("shows status badge", () => {
  render(<OrderDetails order={orderWithItems} />);
  expect(screen.getByText(/Status:/i)).toBeInTheDocument();
});
```

### 4.7 Running All Tests

```bash
# Backend
cd backend && source .venv/bin/activate && python -m pytest tests/ -v --tb=short

# Frontend
cd frontend && npm test
```

---

## 5. Migration Steps

### Phase 0: Preparation

- [ ] Stop all agents: `pkill -f "server.agent_server"`
- [ ] Note: existing in-memory orders are lost (by design - they were per-process)

### Phase 1: Backend Shared Store (independent, do first)

- [ ] Edit `backend/models/order.py` per section 3.1
- [ ] Verify: `python -c "from models.order import create_order, get_order; o = create_order('Test', []); print(get_order(o.id))"`
- [ ] Run: `make test`

### Phase 2: Backend Executor Updates

- [ ] Edit each executor per section 3.2
- [ ] Update `tests/test_executors.py` (SQLite cleanup, order_id in messages)
- [ ] Run: `make test`

### Phase 3: Backend SDK Client

- [ ] Edit `backend/client/sdk_client.py` per section 3.4
- [ ] Optionally update `backend/chat.py` per section 3.5
- [ ] Run tests: `python -m pytest tests/test_sdk_client.py -v`

### Phase 4: Frontend Updates

- [ ] Edit `route.ts` per section 3.6
- [ ] Edit `OrderState.tsx` per section 3.7
- [ ] Edit `Chat.tsx` per section 3.8
- [ ] Edit `OrderDetails.tsx` per section 3.9
- [ ] Run: `cd frontend && npm test`

### Phase 5: Integration

- [ ] Start all agents: `cd backend && python run_all.py`
- [ ] Start frontend: `cd frontend && npm run dev`
- [ ] Place order via UI - verify order_id visible, pipeline completes, status updates from backend

---

## 6. Rollback Plan

All changes are per-file. To rollback:

1. `git checkout backend/models/order.py` - restores in-memory dict
2. `git checkout backend/server/executors/` - restores original executors
3. `git checkout backend/client/sdk_client.py` - removes order_id helpers
4. `git checkout frontend/app/api/copilotkit/[...slug]/route.ts` - removes order_id from tools
5. `git checkout frontend/components/OrderState.tsx` - removes polling
6. `git checkout frontend/components/Chat.tsx` - restores keyword detection
7. `git checkout frontend/components/OrderDetails.tsx` - removes order_id display
8. `rm -f backend/orders.db` - remove SQLite database

---

## Appendix: Complete File Change List

| File | Change |
|------|--------|
| `backend/models/order.py` | Replace `_orders` dict with SQLite; add `order_to_dict`, `embed_order_id`, `extract_order_id`, `update_order`, `update_order_status` |
| `backend/server/executors/fila_executor.py` | Embed `[ORDER_ID: ...]` in reply; parse order_id from input |
| `backend/server/executors/cozinha_executor.py` | Use `get_order(order_id)`; persist with `update_order()`; embed order_id |
| `backend/server/executors/preparo_executor.py` | Same pattern as cozinha |
| `backend/server/executors/entrega_executor.py` | Same pattern as cozinha |
| `backend/server/agent_server.py` | Add `/health` endpoint |
| `backend/client/sdk_client.py` | Add `embed_order_id`, `extract_order_id`, `run_order_pipeline`, `order_id` param to `send_message` |
| `backend/chat.py` | Use `run_order_pipeline` helper |
| `backend/tests/test_models.py` | Replace `_orders.clear()` with SQLite cleanup; add `update_order`, `order_to_dict` tests |
| `backend/tests/test_executors.py` | Replace `_orders.clear()`; use `[ORDER_ID: ...]` in test messages |
| `backend/tests/test_order_id.py` | NEW - order_id embed/extract tests |
| `backend/tests/test_pipeline.py` | NEW - integration tests (require running agents) |
| `frontend/app/api/copilotkit/[...slug]/route.ts` | order_id in all tools; status endpoint; server-side cache |
| `frontend/components/OrderState.tsx` | Add `order_id`, `setOrderId`, `pollOrderStatus`, `STATUS_TO_STEP` |
| `frontend/components/Chat.tsx` | Remove keyword detection; add polling |
| `frontend/components/OrderDetails.tsx` | Show order_id and backend status |
| `frontend/__tests__/OrderState.test.tsx` | Update for new fields |
| `frontend/__tests__/ChatKeywordRegression.test.tsx` | NEW - regression test |
| `frontend/__tests__/OrderDetails.test.tsx` | Add order_id and status tests |
