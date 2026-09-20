# Arquitetura — Pastelaria Virtual A2A

## Visão Geral

Sistema de pedidos de pastel usando Agent-to-Agent (A2A) protocol com frontend CopilotKit.

## Fluxo

```
Browser → CopilotKit (React) → Next.js API Route → BuiltInAgent (LLM + tools)
                                                        ↓
                                              4 A2A JSON-RPC tools
                                                        ↓
                              Backend (4 FastAPI agents: Fila → Cozinha → Preparo → Entrega)
```

1. Usuário digita pedido no chat CopilotKit
2. CopilotKit envia para BuiltInAgent (LLM orquestrador)
3. LLM chama tools na ordem: fila → cozinha → preparo → entrega
4. Cada tool faz HTTP JSON-RPC para o agente A2A correspondente
5. Respostas voltam ao frontend via SSE
6. Timeline atualiza em tempo real por detecção de keywords

## Agentes A2A

| Agente | Porta | Padrão | Função |
|--------|-------|--------|--------|
| Fila | 9001 | Instant | Recebe e enfileira pedido |
| Cozinha | 9002 | Streaming | Prepara com progresso (6 steps) |
| Preparo | 9003 | Instant | Embala o pedido |
| Entrega | 9004 | Instant | Confirma entrega |

## Protocolo

- **Backend ↔ Frontend**: AG-UI (CopilotKit SSE)
- **Backend → A2A Agents**: JSON-RPC 2.0 sobre HTTP (`/a2a/jsonrpc`)
- **Agent Cards**: `/.well-known/agent-card.json`

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, a2a-sdk v1.1.4, uvicorn
- **Frontend**: Next.js 16.3.5, CopilotKit v1.73, Tailwind CSS v4
- **Runtime**: BuiltInAgent (Vercel AI SDK via @ai-sdk/openai) + 4 server-side tools
- **LLM**: Configurável via `OPENAI_BASE_URL` + `LLM_MODEL` (OpenRouter, OpenAI, etc.)

## Cardápio de Pastéis

### Sabores
- 🥩 Carne
- 🍗 Frango
- 🧀 Queijo
- 🌱 Palmito
- 🥩🧀 Carne com Queijo

### Bordas
- Normal
- Queijo
- Catupiry

## Como Rodar

### Docker (recomendado)
```bash
docker compose up -d --build
```

### Local
```bash
# Backend
cd backend && source .venv/bin/activate && python run_all.py

# Frontend
cd frontend && npm run dev
```

### Acessar
- Frontend: http://localhost:3000
- Agentes: http://localhost:9001-9004
