# Sistema de Pedido de Pastel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pastel ordering system with A2A protocol agents (backend) and CopilotKit frontend with real-time timeline showing order status through 5 stages.

**Architecture:** Python FastAPI backend with A2A agents for each order stage (Fila, Cozinha, Preparo, Entrega) orchestrated by an LLM-powered concierge. Next.js frontend with CopilotKit using `@ag-ui/a2a-middleware` to connect to the backend. Real-time timeline via SSE events.

**Tech Stack:** Python 3.10+ (FastAPI, a2a-sdk, httpx), Next.js 14+ (React, CopilotKit, Tailwind CSS)

**Spec:** Brainstorming session — user confirmed: orchestrator + per-stage agents, customizable menu, real-time SSE timeline, LLM + deterministic fallback

---

## Global Constraints

- Python 3.10+ with `protobuf>=4.25,<6`
- Node.js 20+ with npm
- A2A protocol v1.0 with `A2A-Version: 1.0` header
- CopilotKit runtime v2 (`@copilotkit/runtime/v2`)
- No external database needed — in-memory state
- All agents run on localhost with distinct ports (9000-9004)

---

## Review Focus

- Timeline accuracy: Does the frontend timeline reflect the actual backend state at each stage?
- SSE connection reliability: Does the timeline update without manual refresh when agents complete?
- CopilotKit A2A middleware integration: Does the orchestrator correctly dispatch to A2A agents and return results to chat?
- Menu customization: Are all pastel options (sabor, quantidade, borda) correctly parsed and passed through the agent chain?
- Error handling: What happens when an agent is down or returns an error mid-chain?

---

## File Structure

```
ordertaker_a2a/
├── PLAN.md                              ← This file
├── backend/
│   ├── requirements.txt
│   ├── run_all.py                       ← Start all agents + orchestrator
│   ├── chat.py                          ← Terminal chat UI
│   ├── server/
│   │   ├── __init__.py
│   │   ├── agent_server.py              ← FastAPI app + A2A SDK wiring
│   │   └── executors/
│   │       ├── __init__.py
│   │       ├── fila_executor.py         ← Queue agent (instant)
│   │       ├── cozinha_executor.py      ← Kitchen agent (streaming SSE)
│   │       ├── preparo_executor.py      ← Preparation agent (long-running)
│   │       └── entrega_executor.py      ← Delivery agent (instant)
│   ├── client/
│   │   ├── __init__.py
│   │   ├── sdk_client.py                ← A2A protocol helpers
│   │   └── llm_planner.py               ← LLM + deterministic fallback
│   └── models/
│       ├── __init__.py
│       └── order.py                     ← Order data models
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── .env.local
│   └── app/
│       ├── layout.tsx
│       ├── page.tsx
│       ├── providers.tsx
│       ├── globals.css
│       └── api/
│           └── copilotkit/
│               └── [...slug]/
│                   └── route.ts         ← CopilotKit runtime + A2A middleware
└── docs/
    └── architecture.md
```

---

## Task 1: Backend — Data Models & Requirements

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/models/__init__.py`
- Create: `backend/models/order.py`
- Test: `python -c "from models.order import Order; print('OK')"`

- [ ] **Step 1: Create requirements.txt**

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
a2a-sdk>=1.0.0
httpx>=0.25.0
protobuf>=4.25,<6
python-dotenv>=1.0.0
openai>=1.0.0
```

- [ ] **Step 2: Create order data models**

```python
# backend/models/order.py
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import uuid
from datetime import datetime


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
            f"{i.quantidade}x pastel de {i.sabor.value} (borda {i.borda.value})"
            for i in self.itens
        )
        return f"Pedido #{self.id}: {itens_str} — Status: {self.status.value}"


# In-memory order store
_orders: dict[str, Order] = {}


def create_order(cliente_nome: str, itens: list[PastelItem]) -> Order:
    order = Order(cliente_nome=cliente_nome, itens=itens)
    order.timeline["pedido"] = datetime.now().isoformat()
    _orders[order.id] = order
    return order


def get_order(order_id: str) -> Optional[Order]:
    return _orders.get(order_id)


def list_orders() -> list[Order]:
    return list(_orders.values())
```

- [ ] **Step 3: Create __init__.py files**

```python
# backend/models/__init__.py
from .order import (
    Order, OrderStatus, PastelItem, SaborType, BordaType,
    create_order, get_order, list_orders,
)

__all__ = [
    "Order", "OrderStatus", "PastelItem", "SaborType", "BordaType",
    "create_order", "get_order", "list_orders",
]
```

- [ ] **Step 4: Test models**

Run: `cd backend && python -c "from models.order import Order, create_order, PastelItem, SaborType; o = create_order('Teste', [PastelItem(sabor=SaborType.CARNE)]); print(o.to_summary())"`
Expected: `Pedido #xxxx: 1x pastel de carne (borda normal) — Status: pedido`

---

## Task 2: Backend — A2A Client Helpers

**Files:**
- Create: `backend/client/__init__.py`
- Create: `backend/client/sdk_client.py`

- [ ] **Step 1: Create A2A client helpers**

```python
# backend/client/sdk_client.py
"""A2A v1.0 protocol helpers for the pastel ordering system."""
from __future__ import annotations
import asyncio
import uuid
from typing import Any, Callable
import httpx

A2A_HEADERS = {"A2A-Version": "1.0", "Content-Type": "application/json"}

AGENT_URLS = {
    "fila": "http://127.0.0.1:9001",
    "cozinha": "http://127.0.0.1:9002",
    "preparo": "http://127.0.0.1:9003",
    "entrega": "http://127.0.0.1:9004",
}

STREAMING_SKILLS = {"preparar_pastel"}


async def discover_agents(agent_urls: dict[str, str] | None = None) -> list[dict[str, Any]]:
    urls = agent_urls or AGENT_URLS
    agents: list[dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        for name, url in urls.items():
            try:
                resp = await client.get(f"{url}/.well-known/agent-card.json", timeout=5)
                card = resp.json()
                card["_base_url"] = url
                card["_jsonrpc_url"] = f"{url}/a2a/jsonrpc"
                card["_name"] = name
                agents.append(card)
            except Exception:
                pass
    return agents


def extract_reply_text(result: dict) -> str:
    task = result.get("task", result)
    for artifact in task.get("artifacts", []):
        for part in artifact.get("parts", []):
            if isinstance(part, dict) and part.get("text"):
                return part["text"]
    status = task.get("status", {})
    if isinstance(status, dict):
        msg = status.get("message", {})
        if isinstance(msg, dict):
            for part in msg.get("parts", []):
                if isinstance(part, dict) and part.get("text"):
                    return part["text"]
    msg = result.get("message", {})
    if isinstance(msg, dict):
        for part in msg.get("parts", []):
            if isinstance(part, dict) and part.get("text"):
                return part["text"]
    for part in result.get("parts", []):
        if isinstance(part, dict) and part.get("text"):
            return part["text"]
    return str(result)[:200]


async def send_message(
    client: httpx.AsyncClient,
    jsonrpc_url: str,
    text: str,
    return_immediately: bool = False,
) -> dict:
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


async def poll_task(
    client: httpx.AsyncClient,
    jsonrpc_url: str,
    task_id: str,
    on_progress: Callable[[str], Any] | None = None,
    poll_interval: float = 2.0,
    max_polls: int = 30,
) -> str:
    seen: set[str] = set()
    for _ in range(max_polls):
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "GetTask",
            "params": {"id": task_id},
        }
        resp = await client.post(jsonrpc_url, json=payload, headers=A2A_HEADERS, timeout=10)
        body = resp.json()
        if "error" in body:
            raise RuntimeError(f"GetTask error: {body['error']}")
        result = body.get("result", {})
        task = result.get("task", result)
        status = task.get("status", {})
        state = status.get("state", "")
        msg = status.get("message", {})
        if isinstance(msg, dict):
            for part in msg.get("parts", []):
                if isinstance(part, dict) and part.get("text"):
                    txt = part["text"]
                    if txt not in seen and on_progress:
                        seen.add(txt)
                        on_progress(txt)
        if "COMPLETED" in state:
            return extract_reply_text(result)
        if "CANCELED" in state or "FAILED" in state:
            raise RuntimeError(f"Task {state}: {extract_reply_text(result)}")
        await asyncio.sleep(poll_interval)
    raise RuntimeError(f"Task {task_id} timed out after {max_polls} polls")


def get_task_id(result: dict) -> str:
    task = result.get("task", result)
    return task.get("id", "")
```

- [ ] **Step 2: Create __init__.py**

```python
# backend/client/__init__.py
```

---

## Task 3: Backend — Agent Executors (Fila, Cozinha, Preparo, Entrega)

**Files:**
- Create: `backend/server/__init__.py`
- Create: `backend/server/executors/__init__.py`
- Create: `backend/server/executors/fila_executor.py`
- Create: `backend/server/executors/cozinha_executor.py`
- Create: `backend/server/executors/preparo_executor.py`
- Create: `backend/server/executors/entrega_executor.py`

- [ ] **Step 1: Create fila_executor.py (instant response)**

```python
# backend/server/executors/fila_executor.py
"""Fila agent — receives order, places in queue, returns position."""
from __future__ import annotations
import asyncio
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from models.order import create_order, PastelItem, SaborType, BordaType


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
        "carne": SaborType.CARNE,
        "frango": SaborType.FRANGO,
        "queijo": SaborType.QUEIJO,
        "palmito": SaborType.PALMITO,
        "carne com queijo": SaborType.CARNE_QUEIJO,
        "carne e queijo": SaborType.CARNE_QUEIJO,
    }

    for sabor_name, sabor_type in sabores_map.items():
        if sabor_name in text_lower:
            qty = 1
            if f"{sabor_name}" in text_lower:
                import re
                pattern = rf"(\d+)\s*(?:x\s*)?{re.escape(sabor_name)}"
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

        await event_queue.enqueue_event(
            Message(role=Role.agent, parts=[Part(text=reply)])
        )
```

- [ ] **Step 2: Create cozinha_executor.py (streaming)**

```python
# backend/server/executors/cozinha_executor.py
"""Cozinha agent — streaming preparation progress via SSE."""
from __future__ import annotations
import asyncio
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from models.order import list_orders, OrderStatus


class CozinhaExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = ""
        for part in context.message.parts:
            if hasattr(part, "text") and part.text:
                user_text = part.text
                break

        orders = list_orders()
        active = [o for o in orders if o.status in (OrderStatus.FILA, OrderStatus.COZINHA)]

        if not active:
            await event_queue.enqueue_event(
                Message(role=Role.agent, parts=[Part(text="🍳 Nenhum pedido na cozinha no momento.")])
            )
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
            await event_queue.enqueue_event(
                Message(role=Role.agent, parts=[Part(text=step)])
            )
            await asyncio.sleep(1.5)

        order.advance()  # COZINHA -> PREPARO
        await event_queue.enqueue_event(
            Message(
                role=Role.agent,
                parts=[Part(text=f"🎯 Pedido #{order.id} saiu da cozinha e está no preparo.")]
            )
        )
```

- [ ] **Step 3: Create preparo_executor.py (long-running)**

```python
# backend/server/executors/preparo_executor.py
"""Preparo agent — long-running task with progress polling."""
from __future__ import annotations
import asyncio
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.task_store import InMemoryTaskStore, TaskState
from a2a.types import Message, Part, Role, Task, TaskStatus

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from models.order import list_orders, OrderStatus


class PreparoExecutor(AgentExecutor):
    def __init__(self, task_store: InMemoryTaskStore):
        self.task_store = task_store

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = ""
        for part in context.message.parts:
            if hasattr(part, "text") and part.text:
                user_text = part.text
                break

        orders = list_orders()
        active = [o for o in orders if o.status == OrderStatus.PREPARO]

        if not active:
            await event_queue.enqueue_event(
                Message(role=Role.agent, parts=[Part(text="📦 Nenhum pedido para preparar.")])
            )
            return

        order = active[-1]

        steps = [
            ("📦 Enfatando a embalagem...", 30),
            ("🏷️ Colocando etiqueta do pedido...", 50),
            ("✅ Pronto para entrega!", 100),
        ]

        for msg, progress in steps:
            await event_queue.enqueue_event(
                Message(role=Role.agent, parts=[Part(text=msg)])
            )
            await asyncio.sleep(2)

        order.advance()  # PREPARO -> ENTREGA
        await event_queue.enqueue_event(
            Message(
                role=Role.agent,
                parts=[Part(text=f"🚗 Pedido #{order.id} saiu para entrega!")]
            )
        )
```

- [ ] **Step 4: Create entrega_executor.py (instant)**

```python
# backend/server/executors/entrega_executor.py
"""Entrega agent — confirms delivery."""
from __future__ import annotations
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from models.order import list_orders, OrderStatus


class EntregaExecutor(AgentExecutor):
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
                parts=[Part(
                    text=(
                        f"🎉 Pedido #{order.id} entregue com sucesso!\n"
                        f"Cliente: {order.cliente_nome}\n"
                        f"Status: CONCLUÍDO\n"
                        f"Obrigado pela preferência! 🥟"
                    )
                )]
            )
        )
```

- [ ] **Step 5: Create __init__.py files**

```python
# backend/server/__init__.py
```

```python
# backend/server/executors/__init__.py
```

---

## Task 4: Backend — Agent Server (FastAPI + A2A SDK)

**Files:**
- Create: `backend/server/agent_server.py`

- [ ] **Step 1: Create agent_server.py**

```python
# backend/server/agent_server.py
"""FastAPI agent server — each agent runs on its own port."""
from __future__ import annotations
import uvicorn
from a2a.server.apps.a2a import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.task_store import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server.executors.fila_executor import FilaExecutor
from server.executors.cozinha_executor import CozinhaExecutor
from server.executors.preparo_executor import PreparoExecutor
from server.executors.entrega_executor import EntregaExecutor


AGENT_CONFIGS = {
    "fila": {
        "port": 9001,
        "name": "Pastel Fila Agent",
        "description": "Gerencia a fila de pedidos de pastel",
        "skill_id": "receber_pedido",
        "skill_name": "Receber Pedido",
        "tags": ["fila", "pedido", "pastel"],
        "streaming": False,
    },
    "cozinha": {
        "port": 9002,
        "name": "Pastel Cozinha Agent",
        "description": "Gerencia a preparação na cozinha com progresso streaming",
        "skill_id": "preparar_pastel",
        "skill_name": "Preparar Pastel",
        "tags": ["cozinha", "preparo", "fritura"],
        "streaming": True,
    },
    "preparo": {
        "port": 9003,
        "name": "Pastel Preparo Agent",
        "description": "Gerencia o preparo final e embalagem",
        "skill_id": "embalar_pedido",
        "skill_name": "Embalar Pedido",
        "tags": ["preparo", "embalagem"],
        "streaming": False,
    },
    "entrega": {
        "port": 9004,
        "name": "Pastel Entrega Agent",
        "description": "Gerencia a entrega do pedido ao cliente",
        "skill_id": "entregar_pedido",
        "skill_name": "Entregar Pedido",
        "tags": ["entrega", "delivery"],
        "streaming": False,
    },
}

EXECUTORS = {
    "fila": FilaExecutor,
    "cozinha": CozinhaExecutor,
    "preparo": PreparoExecutor,
    "entrega": EntregaExecutor,
}


def build_agent_card(config: dict) -> AgentCard:
    return AgentCard(
        name=config["name"],
        description=config["description"],
        url=f"http://127.0.0.1:{config['port']}",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=config["streaming"]),
        skills=[
            AgentSkill(
                id=config["skill_id"],
                name=config["skill_name"],
                description=config["description"],
                tags=config["tags"],
            )
        ],
    )


def create_app(agent_type: str):
    config = AGENT_CONFIGS[agent_type]
    card = build_agent_card(config)
    task_store = InMemoryTaskStore()

    if agent_type == "preparo":
        executor = PreparoExecutor(task_store)
    else:
        executor = EXECUTORS[agent_type]()

    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
    )

    app = A2AStarletteApplication(
        agent_card=card,
        http_handler=handler,
    )

    return app.build()


def run_agent(agent_type: str):
    config = AGENT_CONFIGS[agent_type]
    app = create_app(agent_type)
    print(f"🚀 Starting {config['name']} on port {config['port']}")
    uvicorn.run(app, host="0.0.0.0", port=config["port"])


if __name__ == "__main__":
    import sys
    agent_type = sys.argv[1] if len(sys.argv) > 1 else "fila"
    if agent_type not in AGENT_CONFIGS:
        print(f"Unknown agent: {agent_type}. Choose from: {list(AGENT_CONFIGS.keys())}")
        sys.exit(1)
    run_agent(agent_type)
```

---

## Task 5: Backend — LLM Planner + Deterministic Fallback

**Files:**
- Create: `backend/client/llm_planner.py`
- Create: `backend/.env.example`

- [ ] **Step 1: Create llm_planner.py**

```python
# backend/client/llm_planner.py
"""LLM planner with deterministic fallback for order orchestration."""
from __future__ import annotations
import os
import json
from typing import Optional

try:
    from openai import OpenAI
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


SYSTEM_PROMPT = """Você é um atendente de pastelaria virtual. Seu trabalho é:

1. Entender o pedido do cliente (sabores, quantidade, borda, observações)
2. Responder confirmando o pedido
3. Retornar um JSON com o pedido estruturado

Exemplo de resposta JSON que você DEVE incluir na sua resposta:
```json
{"nome": "Cliente", "itens": [{"sabor": "carne", "quantidade": 2, "borda": "normal", "observacoes": ""}]}
```

Sabores disponíveis: carne, frango, queijo, palmito, carne_com_queijo
Bordas disponíveis: normal, queijo, catupiry

Seja simpático e Use emojis! 🥟
"""


def plan_with_llm(user_message: str) -> Optional[dict]:
    """Try to plan order using LLM. Returns None if LLM unavailable."""
    if not HAS_LLM:
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
        )
        content = response.choices[0].message.content or ""

        # Extract JSON from response
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
            return json.loads(json_str)

        return None
    except Exception:
        return None


def plan_deterministic(user_message: str) -> dict:
    """Deterministic order parsing without LLM."""
    from server.executors.fila_executor import parse_order_text
    nome, itens = parse_order_text(user_message)
    return {
        "nome": nome,
        "itens": [
            {"sabor": i.sabor.value, "quantidade": i.quantidade, "borda": i.borda.value, "observacoes": i.observacoes}
            for i in itens
        ],
    }


def plan_order(user_message: str) -> tuple[str, dict]:
    """Plan order: try LLM first, fallback to deterministic.
    Returns (response_text, order_data).
    """
    llm_result = plan_with_llm(user_message)
    if llm_result:
        return "", llm_result

    order_data = plan_deterministic(user_message)
    itens_str = ", ".join(
        f"{i['quantidade']}x pastel de {i['sabor']}" for i in order_data["itens"]
    )
    response = f"Pedido confirmado! {itens_str}. Enviando para a fila... 🥟"
    return response, order_data
```

- [ ] **Step 2: Create .env.example**

```
# LLM Configuration (optional — deterministic fallback works without it)
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4o-mini

# Or use AWS Bedrock:
# AWS_REGION=us-east-1
# BEDROCK_MODEL=anthropic.claude-3-haiku-20240307-v1:0
```

---

## Task 6: Backend — Run All + Chat Terminal

**Files:**
- Create: `backend/run_all.py`
- Create: `backend/chat.py`

- [ ] **Step 1: Create run_all.py**

```python
# backend/run_all.py
"""Start all A2A agents as background processes."""
from __future__ import annotations
import subprocess
import sys
import time
import signal
import os

AGENTS = ["fila", "cozinha", "preparo", "entrega"]
PORTS = {"fila": 9001, "cozinha": 9002, "preparo": 9003, "entrega": 9004}


def main():
    processes: list[subprocess.Popen] = []
    print("🥟 Pastel A2A System — Starting all agents...\n")

    for agent in AGENTS:
        proc = subprocess.Popen(
            [sys.executable, "-m", "server.agent_server", agent],
            cwd=os.path.dirname(__file__) or ".",
        )
        processes.append(proc)
        print(f"  ✅ {agent.upper()} agent started (PID: {proc.pid}, port: {PORTS[agent]})")
        time.sleep(0.5)

    print(f"\n🎉 All {len(AGENTS)} agents running!")
    print("Press Ctrl+C to stop all agents.\n")

    def shutdown(sig, frame):
        print("\n🛑 Shutting down all agents...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
        print("👋 All agents stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create chat.py**

```python
# backend/chat.py
"""Terminal chat UI for the pastel ordering system."""
from __future__ import annotations
import asyncio
import httpx

from client.sdk_client import discover_agents, send_message, extract_reply_text, AGENT_URLS


async def main():
    print("🥟 Pastelaria Virtual — Chat de Pedidos")
    print("=" * 50)
    print("Comandos: 'pedido' para fazer pedido, 'sair' para sair")
    print("=" * 50)

    async with httpx.AsyncClient() as client:
        # Discover agents
        print("\n🔍 Descobrindo agentes...")
        try:
            agents = await discover_agents()
            for a in agents:
                print(f"  ✅ {a.get('name', 'Unknown')} @ {a.get('_base_url')}")
        except Exception as e:
            print(f"  ⚠️ Alguns agentes não estão disponíveis: {e}")
            print("  Execute 'python run_all.py' primeiro!")

        print("\n")

        while True:
            user_input = input("Você: ").strip()
            if user_input.lower() in ("sair", "exit", "quit"):
                print("👋 Tchau!")
                break
            if not user_input:
                continue

            # Send to fila agent
            print("\n📋 Enviando para a fila...")
            try:
                result = await send_message(
                    client,
                    f"{AGENT_URLS['fila']}/a2a/jsonrpc",
                    user_input,
                )
                reply = extract_reply_text(result)
                print(f"📋 Fila: {reply}")
            except Exception as e:
                print(f"❌ Erro na fila: {e}")

            # Send to cozinha
            print("\n🍳 Cozinha processando...")
            try:
                result = await send_message(
                    client,
                    f"{AGENT_URLS['cozinha']}/a2a/jsonrpc",
                    "preparar",
                )
                reply = extract_reply_text(result)
                print(f"🍳 Cozinha: {reply}")
            except Exception as e:
                print(f"❌ Erro na cozinha: {e}")

            # Send to preparo
            print("\n📦 Preparo...")
            try:
                result = await send_message(
                    client,
                    f"{AGENT_URLS['preparo']}/a2a/jsonrpc",
                    "embalar",
                    return_immediately=True,
                )
                from client.sdk_client import get_task_id, poll_task
                task_id = get_task_id(result)
                if task_id:
                    reply = await poll_task(
                        client,
                        f"{AGENT_URLS['preparo']}/a2a/jsonrpc",
                        task_id,
                        on_progress=lambda txt: print(f"  📦 {txt}"),
                    )
                    print(f"📦 Preparo: {reply}")
            except Exception as e:
                print(f"❌ Erro no preparo: {e}")

            # Send to entrega
            print("\n🚚 Entrega...")
            try:
                result = await send_message(
                    client,
                    f"{AGENT_URLS['entrega']}/a2a/jsonrpc",
                    "entregar",
                )
                reply = extract_reply_text(result)
                print(f"🚚 Entrega: {reply}")
            except Exception as e:
                print(f"❌ Erro na entrega: {e}")

            print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Task 7: Frontend — Next.js + CopilotKit Setup

**Files:**
- Create: `frontend/package.json` (via npx create-next-app)
- Modify: install CopilotKit packages
- Create: `frontend/.env.local`
- Create: `frontend/app/providers.tsx`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/globals.css`

- [ ] **Step 1: Create Next.js app**

Run: `cd /home/access/AI/ordertaker_a2a && npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm --no-turbopack`

- [ ] **Step 2: Install CopilotKit packages**

Run: `cd /home/access/AI/ordertaker_a2a/frontend && npm install @copilotkit/react-core @copilotkit/runtime @ag-ui/a2a-middleware @ag-ui/client`

- [ ] **Step 3: Create .env.local**

```
OPENAI_API_KEY=your_key_here
COPILOTKIT_API_KEY=your_copilotkit_key_here
```

- [ ] **Step 4: Create providers.tsx**

```tsx
// frontend/app/providers.tsx
"use client";

import { CopilotKitProvider } from "@copilotkit/react-core/v2";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <CopilotKitProvider runtimeUrl="/api/copilotkit">
      {children}
    </CopilotKitProvider>
  );
}
```

- [ ] **Step 5: Update layout.tsx**

```tsx
// frontend/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Pastelaria Virtual — A2A Order System",
  description: "Sistema de pedidos de pastel com A2A protocol e CopilotKit",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 6: Update globals.css**

```css
/* frontend/app/globals.css */
@import "tailwindcss";

:root {
  --background: #ffffff;
  --foreground: #171717;
}

body {
  background: var(--background);
  color: var(--foreground);
  font-family: Arial, Helvetica, sans-serif;
}
```

---

## Task 8: Frontend — CopilotKit Runtime Route with A2A Middleware

**Files:**
- Create: `frontend/app/api/copilotkit/[...slug]/route.ts`

- [ ] **Step 1: Create CopilotKit runtime route**

```typescript
// frontend/app/api/copilotkit/[...slug]/route.ts
import {
  CopilotRuntime,
  createCopilotRuntimeHandler,
  InMemoryAgentRunner,
} from "@copilotkit/runtime/v2";
import { HttpAgent } from "@ag-ui/client";
import { A2AMiddlewareAgent } from "@ag-ui/a2a-middleware";

const filaAgentUrl = process.env.FILA_AGENT_URL || "http://localhost:9001";
const cozinhaAgentUrl = process.env.COZINHA_AGENT_URL || "http://localhost:9002";
const preparoAgentUrl = process.env.PREPARO_AGENT_URL || "http://localhost:9003";
const entregaAgentUrl = process.env.ENTREGA_AGENT_URL || "http://localhost:9004";

// We need an orchestration agent — using the Fila agent as coordinator
// since it's the first step and can delegate to others
const orchestratorUrl = process.env.ORCHESTRATOR_URL || "http://localhost:9001";

const orchestrationAgent = new HttpAgent({
  url: orchestratorUrl,
});

const a2aMiddlewareAgent = new A2AMiddlewareAgent({
  description:
    "Pastelaria virtual com agentes especializados: Fila, Cozinha, Preparo e Entrega",
  agentUrls: [filaAgentUrl, cozinhaAgentUrl, preparoAgentUrl, entregaAgentUrl],
  orchestrationAgent,
  instructions: `
    Você é um atendente de pastelaria virtual. Gerencia pedidos de pastel usando agentes especializados.

    FLUXO DO PEDIDO:
    1. Agente Fila — Recebe o pedido e posiciona na fila
    2. Agente Cozinha — Prepara o pastel (streaming com progresso)
    3. Agente Preparo — Embala o pedido
    4. Agente Entrega — Entrega ao cliente

    SABORES: carne, frango, queijo, palmito, carne_com_queijo
    BORDAS: normal, queijo, catupiry

    REGRAS:
    - Chame os agentes UM POR VEZ, espere o resultado antes de chamar o próximo
    - Passe informações do agente anterior para o próximo
    - Use o agente Fila primeiro para receber o pedido
    - Depois Cozinha, Preparo e Entrega em sequência
    - Ao final, confirme a entrega ao cliente
  `,
});

const runtime = new CopilotRuntime({
  agents: {
    a2a_chat: a2aMiddlewareAgent,
  },
  runner: new InMemoryAgentRunner(),
});

const handler = createCopilotRuntimeHandler({
  runtime,
  basePath: "/api/copilotkit",
});

export const GET = handler;
export const POST = handler;
export const PATCH = handler;
export const DELETE = handler;
```

---

## Task 9: Frontend — Chat UI + Timeline Component

**Files:**
- Create: `frontend/components/Chat.tsx`
- Create: `frontend/components/Timeline.tsx`
- Create: `frontend/components/A2AMessage.tsx`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Create Timeline component**

```tsx
// frontend/components/Timeline.tsx
"use client";

import React from "react";

const STEPS = [
  { key: "pedido", label: "Pedido", icon: "📋", color: "blue" },
  { key: "fila", label: "Fila", icon: "📍", color: "yellow" },
  { key: "cozinha", label: "Cozinha", icon: "🍳", color: "orange" },
  { key: "preparo", label: "Preparo", icon: "📦", color: "purple" },
  { key: "entrega", label: "Entrega", icon: "🚚", color: "green" },
] as const;

interface TimelineProps {
  currentStep: number;
  completedSteps: number[];
}

const colorMap: Record<string, { bg: string; text: string; border: string }> = {
  blue: { bg: "bg-blue-100", text: "text-blue-700", border: "border-blue-400" },
  yellow: { bg: "bg-yellow-100", text: "text-yellow-700", border: "border-yellow-400" },
  orange: { bg: "bg-orange-100", text: "text-orange-700", border: "border-orange-400" },
  purple: { bg: "bg-purple-100", text: "text-purple-700", border: "border-purple-400" },
  green: { bg: "bg-green-100", text: "text-green-700", border: "border-green-400" },
};

export function Timeline({ currentStep, completedSteps }: TimelineProps) {
  return (
    <div className="w-full p-4">
      <h3 className="text-lg font-bold mb-4 text-center">🥟 Status do Pedido</h3>
      <div className="flex items-center justify-between relative">
        {/* Connector line */}
        <div className="absolute top-6 left-0 right-0 h-1 bg-gray-200 z-0" />
        <div
          className="absolute top-6 left-0 h-1 bg-green-500 z-10 transition-all duration-500"
          style={{ width: `${(completedSteps.length / (STEPS.length - 1)) * 100}%` }}
        />

        {STEPS.map((step, idx) => {
          const isCompleted = completedSteps.includes(idx);
          const isCurrent = currentStep === idx;
          const colors = colorMap[step.color];

          return (
            <div key={step.key} className="flex flex-col items-center relative z-20">
              <div
                className={`
                  w-12 h-12 rounded-full flex items-center justify-center text-xl
                  border-2 transition-all duration-300
                  ${isCompleted ? "bg-green-500 border-green-500 text-white" : ""}
                  ${isCurrent ? `${colors.bg} ${colors.border} ${colors.text} animate-pulse` : ""}
                  ${!isCompleted && !isCurrent ? "bg-gray-100 border-gray-300 text-gray-400" : ""}
                `}
              >
                {isCompleted ? "✓" : step.icon}
              </div>
              <span
                className={`
                  mt-2 text-xs font-medium
                  ${isCompleted || isCurrent ? "text-gray-900" : "text-gray-400"}
                `}
              >
                {step.label}
              </span>
              {isCurrent && (
                <span className="text-[10px] text-gray-500 animate-pulse">atual</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create A2A Message components**

```tsx
// frontend/components/A2AMessage.tsx
"use client";

import React from "react";

type MessageActionRenderProps = {
  status: string;
  args: {
    agentName?: string;
    task?: string;
  };
};

const agentStyles: Record<string, { icon: string; bgColor: string; textColor: string; borderColor: string }> = {
  "Pastel Fila Agent": { icon: "📋", bgColor: "bg-yellow-50", textColor: "text-yellow-700", borderColor: "border-yellow-300" },
  "Pastel Cozinha Agent": { icon: "🍳", bgColor: "bg-orange-50", textColor: "text-orange-700", borderColor: "border-orange-300" },
  "Pastel Preparo Agent": { icon: "📦", bgColor: "bg-purple-50", textColor: "text-purple-700", borderColor: "border-purple-300" },
  "Pastel Entrega Agent": { icon: "🚚", bgColor: "bg-green-50", textColor: "text-green-700", borderColor: "border-green-300" },
};

function getAgentStyle(name: string) {
  return agentStyles[name] || { icon: "🤖", bgColor: "bg-gray-50", textColor: "text-gray-700", borderColor: "border-gray-300" };
}

function truncateTask(task: string, maxLen = 80) {
  return task.length > maxLen ? task.slice(0, maxLen) + "..." : task;
}

export function MessageToA2A({ status, args }: MessageActionRenderProps) {
  switch (status) {
    case "executing":
    case "complete":
      break;
    default:
      return null;
  }

  if (!args.agentName || !args.task) return null;

  const style = getAgentStyle(args.agentName);

  return (
    <div className={`${style.bgColor} border ${style.borderColor} rounded-lg px-4 py-3 my-2`}>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-gray-700 text-white">
            Orquestrador
          </span>
          <span className="text-gray-400 text-sm">→</span>
          <span className={`px-3 py-1 rounded-full text-xs font-semibold border-2 ${style.bgColor} ${style.textColor} ${style.borderColor}`}>
            {style.icon} {args.agentName}
          </span>
        </div>
        <span className="text-gray-700 text-sm flex-1">{truncateTask(args.task)}</span>
      </div>
    </div>
  );
}

export function MessageFromA2A({ status, args }: MessageActionRenderProps) {
  if (status !== "complete" || !args.agentName) return null;

  const style = getAgentStyle(args.agentName);

  return (
    <div className="my-2">
      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full text-xs font-semibold border-2 ${style.bgColor} ${style.textColor} ${style.borderColor}`}>
            {style.icon} {args.agentName}
          </span>
          <span className="text-gray-400 text-sm">→</span>
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-gray-700 text-white">
            Orquestrador
          </span>
          <span className="text-xs text-green-600">✓ Resposta recebida</span>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create Chat component**

```tsx
// frontend/components/Chat.tsx
"use client";

import React, { useState } from "react";
import { CopilotSidebar } from "@copilotkit/react-core/v2";
import { useFrontendTool } from "@copilotkit/react-core/v2";
import { Timeline } from "./Timeline";
import { MessageToA2A, MessageFromA2A } from "./A2AMessage";

const STEP_KEYWORDS: Record<string, number> = {
  pedido: 0,
  fila: 1,
  cozinha: 2,
  preparo: 3,
  entrega: 4,
  concluido: 4,
};

function detectStep(text: string): number {
  const lower = text.toLowerCase();
  for (const [keyword, step] of Object.entries(STEP_KEYWORDS)) {
    if (lower.includes(keyword)) return step;
  }
  return -1;
}

export function Chat() {
  const [currentStep, setCurrentStep] = useState(-1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  useFrontendTool({
    name: "send_message_to_a2a_agent",
    description: "Envia uma mensagem para um agente A2A",
    available: "frontend",
    parameters: [
      { name: "agentName", type: "string", description: "Nome do agente A2A" },
      { name: "task", type: "string", description: "Mensagem para o agente" },
    ],
    render: (props) => {
      const step = detectStep(props.args.task || "");
      if (step >= 0) {
        setCurrentStep(step);
        setCompletedSteps((prev) => {
          const newCompleted = [...prev];
          for (let i = 0; i < step; i++) {
            if (!newCompleted.includes(i)) newCompleted.push(i);
          }
          return newCompleted;
        });
      }

      return (
        <>
          <MessageToA2A {...props} />
          <MessageFromA2A {...props} />
        </>
      );
    },
  });

  return (
    <div className="flex h-screen">
      <div className="w-full max-w-2xl mx-auto flex flex-col">
        {/* Timeline */}
        <div className="border-b bg-white sticky top-0 z-10">
          <Timeline
            currentStep={currentStep}
            completedSteps={completedSteps}
          />
        </div>

        {/* Chat */}
        <div className="flex-1 overflow-hidden">
          <CopilotSidebar
            defaultOpen={true}
            labels={{
              title: "🥟 Pastelaria Virtual",
              initial:
                "Olá! Bem-vindo à Pastelaria Virtual! 🥟\n\nFaça seu pedido! Exemplo:\n- 2 pastéis de carne com borda de catupiry\n- 1 pastel de frango e 1 de queijo\n- Pastel de palmito sem cebola",
            }}
          />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Update page.tsx**

```tsx
// frontend/app/page.tsx
"use client";

import { Chat } from "@/components/Chat";

export default function Page() {
  return <Chat />;
}
```

---

## Task 10: Integration Test & Documentation

**Files:**
- Create: `docs/architecture.md`

- [ ] **Step 1: Create architecture docs**

```markdown
# Arquitetura — Pastelaria Virtual A2A

## Visão Geral

Sistema de pedidos de pastel usando Agent-to-Agent (A2A) protocol com frontend CopilotKit.

## Fluxo

1. Usuário digita pedido no chat CopilotKit
2. CopilotKit encaminha via AG-UI para o Orquestrador
3. Orquestrador usa LLM (ou fallback determinístico) para parse do pedido
4. Orquestrador despacha para agentes A2A em sequência:
   - Fila (9001) → Cozinha (9002) → Preparo (9003) → Entrega (9004)
5. Respostas voltam ao frontend via SSE
6. Timeline atualiza em tempo real

## Agentes

| Agente | Porta | Padrão | Função |
|--------|-------|--------|--------|
| Fila | 9001 | Instant | Recebe e enfileira pedido |
| Cozinha | 9002 | Streaming | Prepara com progresso |
| Preparo | 9003 | Long-running | Embala com polling |
| Entrega | 9004 | Instant | Confirma entrega |

## Tech Stack

- Backend: Python 3.10+, FastAPI, a2a-sdk v1.0
- Frontend: Next.js 14+, CopilotKit v2, Tailwind CSS
- Protocolo: A2A v1.0 + AG-UI
```

- [ ] **Step 2: Test the full system**

Run: `cd backend && python -m run_all`
Run: `cd frontend && npm run dev`
Open: http://localhost:3000
Test: Type "2 pastéis de carne com borda de catupiry" in chat
