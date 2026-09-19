"""A2A v1.0 protocol helpers for the pastel ordering system."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from typing import Any

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
            except Exception:  # noqa: S110 — agent may be offline
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
