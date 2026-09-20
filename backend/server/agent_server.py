"""FastAPI agent server — each agent runs on its own port."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from a2a.server.routes import create_jsonrpc_routes, create_agent_card_routes
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

from server.executors.fila_executor import FilaExecutor
from server.executors.cozinha_executor import CozinhaExecutor
from server.executors.preparo_executor import PreparoExecutor
from server.executors.entrega_executor import EntregaExecutor

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

AGENT_CONFIGS = {
    "fila": {
        "port": int(os.getenv("FILA_PORT", "9001")),
        "name": "Pastel Fila Agent",
        "description": "Gerencia a fila de pedidos de pastel",
        "skill_id": "receber_pedido",
        "skill_name": "Receber Pedido",
        "tags": ["fila", "pedido", "pastel"],
        "streaming": False,
    },
    "cozinha": {
        "port": int(os.getenv("COZINHA_PORT", "9002")),
        "name": "Pastel Cozinha Agent",
        "description": "Gerencia a preparação na cozinha com progresso streaming",
        "skill_id": "preparar_pastel",
        "skill_name": "Preparar Pastel",
        "tags": ["cozinha", "preparo", "fritura"],
        "streaming": True,
    },
    "preparo": {
        "port": int(os.getenv("PREPARO_PORT", "9003")),
        "name": "Pastel Preparo Agent",
        "description": "Gerencia o preparo final e embalagem",
        "skill_id": "embalar_pedido",
        "skill_name": "Embalar Pedido",
        "tags": ["preparo", "embalagem"],
        "streaming": False,
    },
    "entrega": {
        "port": int(os.getenv("ENTREGA_PORT", "9004")),
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


def create_app(agent_type: str) -> FastAPI:
    config = AGENT_CONFIGS[agent_type]
    card = build_agent_card(config)
    task_store = InMemoryTaskStore()

    executor = EXECUTORS[agent_type]()

    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        agent_card=card,
    )

    app = FastAPI()

    # CORS — configurable origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
        allow_credentials=CORS_ORIGINS != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add A2A routes
    jsonrpc_routes = create_jsonrpc_routes(
        request_handler=handler,
        rpc_url="/a2a/jsonrpc",
    )
    card_routes = create_agent_card_routes(agent_card=card)

    for route in jsonrpc_routes + card_routes:
        app.routes.append(route)

    # Alias: CopilotKit fetches /.well-known/agent.json but SDK serves agent-card.json
    # Also inject the `url` field that CopilotKit A2A middleware requires
    from starlette.requests import Request as StarletteRequest
    from starlette.responses import JSONResponse as StarletteJSONResponse
    from a2a.server.request_handlers.response_helpers import agent_card_to_dict

    def _card_with_url() -> dict:
        card_dict = agent_card_to_dict(card)
        card_dict["url"] = f"http://127.0.0.1:{config['port']}"
        return card_dict

    async def agent_card_alias(request: StarletteRequest) -> StarletteJSONResponse:
        return StarletteJSONResponse(_card_with_url())

    from starlette.routing import Route
    app.routes.append(Route("/.well-known/agent.json", endpoint=agent_card_alias, methods=["GET"]))

    # Also override the standard path to include url
    async def agent_card_standard(request: StarletteRequest) -> StarletteJSONResponse:
        return StarletteJSONResponse(_card_with_url())

    app.routes.append(Route("/.well-known/agent-card.json", endpoint=agent_card_standard, methods=["GET"]))

    return app


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
