# 🥟 Pastelaria Virtual — A2A Order System

Sistema de pedidos de pastel usando **Agent-to-Agent (A2A) protocol** com frontend **CopilotKit** e timeline em tempo real.

![Architecture](docs/architecture.md)

## 🚀 Quick Start

### Com Docker (recomendado)

```bash
# Build e rodar
make docker-up

# Acessar
open http://localhost:3000
```

### Sem Docker

```bash
# Setup inicial
make setup

# Rodar (backend + frontend)
make dev

# Acessar
open http://localhost:3000
```

## 📋 Cardápio de Pastéis

| Sabor | Descrição |
|-------|-----------|
| 🥩 Carne | Pastel clássico de carne moída |
| 🍗 Frango | Frango desfiado com tempero |
| 🧀 Queijo | Queijo derretido |
| 🥬 Palmito | Palmito com ervas |
| 🥩🧀 Carne com Queijo | Combinação especial |

**Bordas:** Normal, Queijo, Catupiry

### Exemplos de Pedido

```
2 pastéis de carne com borda de catupiry
1 pastel de frango e 1 de queijo
5 pastéis de palmito borda queijo
```

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js + CopilotKit)                        │
│  ┌───────────┐  ┌─────────────────────────────────────┐ │
│  │  Chat UI  │  │  Timeline (5 etapas animadas)       │ │
│  │(sidebar)  │  │  Pedido → Fila → Cozinha → Prep → Ent│ │
│  └─────┬─────┘  └──────────────┬──────────────────────┘ │
│        │ AG-UI                 │ SSE                     │
├────────┼───────────────────────┼─────────────────────────┤
│  BACKEND (Python FastAPI)      │                         │
│  ┌─────▼─────────────────────┐ │                         │
│  │  Orquestrador (LLM + det) │ │                         │
│  └──┬──────┬──────┬──────┬───┘ │                         │
│     │      │      │      │     │                         │
│  ┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐ │                         │
│  │Fila ││Coz. ││Prep.││Ent. │ │                         │
│  │ 9001││ 9002││ 9003││ 9004│ │                         │
│  └─────┘└─────┘└─────┘└─────┘ │                         │
└─────────────────────────────────────────────────────────┘
```

### Agentes A2A

| Agente | Porta | Padrão | Função |
|--------|-------|--------|--------|
| 📋 Fila | 9001 | Instant | Recebe e enfileira pedido |
| 🍳 Cozinha | 9002 | Streaming | Prepara com progresso SSE |
| 📦 Preparo | 9003 | Long-running | Embala com polling |
| 🚚 Entrega | 9004 | Instant | Confirma entrega |

### Fluxo

1. Usuário digita pedido no chat CopilotKit
2. CopilotKit encaminha via AG-UI para o Orquestrador
3. Orquestrador usa LLM (ou fallback determinístico) para parse
4. Despacha para agentes A2A em sequência: Fila → Cozinha → Preparo → Entrega
5. Timeline atualiza em tempo real no frontend

## 🛠️ Tech Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | Next.js 16, CopilotKit v2, Tailwind CSS |
| Protocolo | A2A v1.0, AG-UI |
| Backend | Python 3.11, FastAPI, a2a-sdk |
| LLM | OpenAI (opcional, fallback determinístico) |
| Infra | Docker, Docker Compose |

## 📁 Estrutura do Projeto

```
ordertaker_a2a/
├── backend/
│   ├── models/          # Order data models
│   ├── client/          # A2A helpers + LLM planner
│   ├── server/          # Agent servers + executors
│   ├── tests/           # 40 pytest tests (TDD)
│   ├── run_all.py       # Start all agents
│   ├── chat.py          # Terminal chat
│   ├── check.sh         # All checks (lint+format+test)
│   └── pyproject.toml   # Config (ruff, pytest)
├── frontend/
│   ├── app/             # Next.js app router
│   │   ├── api/copilotkit/  # A2A middleware route
│   │   ├── providers.tsx    # CopilotKit provider
│   │   └── page.tsx         # Main page
│   └── components/      # Timeline, Chat, A2A messages
├── docs/                # Architecture docs
├── docker-compose.yml   # Docker orchestration
├── Makefile             # Dev commands
├── PLAN.md              # Implementation plan
└── README.md            # This file
```

## 🧪 Desenvolvimento

### Comandos

```bash
make help              # Ver todos os comandos
make setup             # Setup inicial
make test              # Rodar testes
make lint              # Lint (ruff check)
make format            # Formatar código
make check             # Todos os checks
make dev               # Rodar tudo
make docker-up         # Docker
```

### TDD (Test-Driven Development)

O projeto segue TDD com 40 testes cobrindo:
- Modelos de dados (Order, PastelItem)
- Parser de pedidos (quantidade, sabores, bordas)
- Cliente A2A (extração de respostas)
- LLM planner (fallback determinístico)

```bash
make test              # Rodar todos
make test-watch        # Modo watch
```

### Linter & Formatação

```bash
make lint              # Verificar
make format            # Formatar
make format-check      # Checar sem alterar
```

## 🔧 Configuração

### Variáveis de Ambiente

```bash
# Backend (.env)
OPENAI_API_KEY=sk-...     # Opcional (fallback determinístico)
LLM_MODEL=gpt-4o-mini

# Frontend (.env.local)
OPENAI_API_KEY=sk-...     # Opcional
```

### Sem LLM

O sistema funciona sem LLM usando parsing determinístico. Apenas configure o cardápio e faça pedidos no formato:

```
2 pastéis de carne com borda de catupiry
```

## 📚 Documentação

- [Arquitetura](docs/architecture.md)
- [Plano de Implementação](PLAN.md)
- [A2A Protocol](https://a2a-protocol.org/latest/)
- [CopilotKit Docs](https://docs.copilotkit.ai)

## 🐛 Troubleshooting

### Agentes não iniciam

```bash
# Verificar portas
lsof -i :9001-9004

# Reiniciar
make docker-down && make docker-up
```

### Frontend não conecta ao backend

```bash
# Verificar se agentes estão rodando
curl http://localhost:9001/.well-known/agent-card.json
```

### Testes falham

```bash
cd backend && source .venv/bin/activate
ruff check .            # Verificar lint
python -m pytest tests/ -v  # Ver testes
```

## 📄 License

MIT
