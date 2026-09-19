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

## Cardápio de Pastéis

### Sabores
- 🥩 Carne
- 🍗 Frango
- 🧀 Queijo
- 🥬 Palmito
- 🥩🧀 Carne com Queijo

### Bordas
- Normal
- Queijo
- Catupiry

## Como Rodar

### Backend
```bash
cd backend
pip install -r requirements.txt
python run_all.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Acessar
- Frontend: http://localhost:3000
- Agentes: http://localhost:9001-9004
