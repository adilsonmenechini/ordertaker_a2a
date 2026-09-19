# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ordertaker_a2a** — an Agent-to-Agent (A2A) order-taking system for a pastelaria (Brazilian pastry shop). Uses A2A protocol agents on the backend with a CopilotKit frontend featuring a real-time order timeline.

## Directory Structure

```
ordertaker_a2a/
├── backend/           — Python A2A agents (FastAPI + a2a-sdk)
│   ├── models/        — Order data models
│   ├── client/        — A2A protocol helpers + LLM planner
│   ├── server/        — Agent servers + executors
│   ├── tests/         — pytest test suite (TDD)
│   ├── run_all.py     — Start all agents
│   └── chat.py        — Terminal chat UI
├── frontend/          — Next.js + CopilotKit
│   ├── app/           — Next.js app router
│   └── components/    — Timeline, Chat, A2A messages
├── docs/              — Architecture documentation
└── PLAN.md            — Implementation plan
```

## Tooling

### Backend (Python)
- **Package manager:** `uv` (NOT pip)
- **Linter:** `ruff check .`
- **Formatter:** `ruff format .`
- **Tests:** `pytest` with TDD
- **Type hints:** Python 3.10+

### Frontend (Node.js)
- **Package manager:** npm
- **Framework:** Next.js 16+ with CopilotKit v2
- **Linting:** ESLint (via next.config)
- **Styling:** Tailwind CSS v4

## Common Commands

```bash
# Backend — run all agents
cd backend && source .venv/bin/activate && python run_all.py

# Backend — run tests
cd backend && source .venv/bin/activate && python -m pytest tests/ -v

# Backend — lint + format
cd backend && source .venv/bin/activate && ruff check . && ruff format .

# Frontend — dev server
cd frontend && npm run dev

# Full system
# Terminal 1: cd backend && python run_all.py
# Terminal 2: cd frontend && npm run dev
# Open: http://localhost:3000
```

## A2A Agent Ports

| Agent | Port | Pattern |
|-------|------|---------|
| Fila | 9001 | Instant (blocking) |
| Cozinha | 9002 | Streaming (SSE) |
| Preparo | 9003 | Long-running (polling) |
| Entrega | 9004 | Instant (blocking) |

## Development Notes

- Follow TDD: write failing test first, then implement, then refactor
- Use `ruff` for Python linting and formatting
- All agents use A2A v1.0 protocol with `A2A-Version: 1.0` header
- In-memory order store (no database)
- LLM integration is optional (deterministic fallback works)
