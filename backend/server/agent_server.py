"""FastAPI agent server — each agent runs on its own port."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uvicorn
from a2a.server.apps.a2a import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.task_store import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from server.executors.cozinha_executor import CozinhaExecutor
from server.executors.entrega_executor import EntregaExecutor
from server.executors.fila_executor import FilaExecutor
from server.executors.preparo_executor import PreparoExecutor

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

    executor = PreparoExecutor(task_store) if agent_type == "preparo" else EXECUTORS[agent_type]()

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
    uvicorn.run(app, host="0.0.0.0", port=config["port"])  # noqa: S104 — local dev only


if __name__ == "__main__":
    agent_type = sys.argv[1] if len(sys.argv) > 1 else "fila"
    if agent_type not in AGENT_CONFIGS:
        print(f"Unknown agent: {agent_type}. Choose from: {list(AGENT_CONFIGS.keys())}")
        sys.exit(1)
    run_agent(agent_type)
