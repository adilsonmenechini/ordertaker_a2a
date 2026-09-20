"""LLM planner with deterministic fallback for order orchestration."""

from __future__ import annotations

import json
import os

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
{"nome": "Cliente", "itens": [{"sabor": "carne", "quantidade": 2, "borda": "normal"}]}
```

Sabores disponíveis: carne, frango, queijo, palmito, carne_com_queijo
Bordas disponíveis: normal, queijo, catupiry

Seja simpático e Use emojis! 🥟
"""


def _clean_api_key(api_key: str) -> str:
    """Remove non-ASCII characters from API key."""
    return api_key.encode("ascii", "ignore").decode("ascii")


def plan_with_llm(user_message: str) -> dict | None:
    """Try to plan order using LLM. Returns None if LLM unavailable."""
    if not HAS_LLM:
        return None

    raw_key = os.getenv("OPENAI_API_KEY")
    if not raw_key:
        return None

    api_key = _clean_api_key(raw_key)
    if not api_key:
        return None

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL"),
        )
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
            {
                "sabor": i.sabor.value,
                "quantidade": i.quantidade,
                "borda": i.borda.value,
                "observacoes": i.observacoes,
            }
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
    itens_str = ", ".join(f"{i['quantidade']}x pastel de {i['sabor']}" for i in order_data["itens"])
    response = f"Pedido confirmado! {itens_str}. Enviando para a fila... 🥟"
    return response, order_data
