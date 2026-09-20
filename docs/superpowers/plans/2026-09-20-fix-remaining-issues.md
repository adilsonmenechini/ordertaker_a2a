# Fix All Remaining Issues — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix LLM auth, streaming capture, Docker build, and ensure end-to-end chat works

**Architecture:** CopilotKit BuiltInAgent (LLM) calls 4 server-side tools that POST to A2A JSON-RPC backends. Timeline updates via keyword detection in chat messages.

**Tech Stack:** Next.js 16.3.5, CopilotKit v1.73, @ai-sdk/openai, zod, FastAPI, a2a-sdk v1.1.4, Docker

---

## Global Constraints

- SDD → TDD (RED/GREEN/REFACTOR) → Linter → Safety for EVERY change
- No production code without failing test first
- Ruff line-length: 100, TypeScript strict
- All env vars documented in .env.example

---

## Review Focus

| Input/Failure Mode | Expected Behavior | Test Owner |
|--------------------|-------------------|------------|
| LLM API key with special chars | Cleaned/validated before use | Task 1 |
| Cozinha streaming progress | All steps captured, not just last | Task 2 |
| Frontend timeline sync | Keywords in LLM response update step | Task 3 |
| Docker build | Frontend compiles in <5min, all agents healthy | Task 4 |
| Chat end-to-end | User types → LLM → tools → agents → timeline | Task 5 |

---

### Task 1: Fix LLM API Key (Unicode Issue)

**Files:**
- Modify: `.env` (clean the key)
- Modify: `.env.example` (document key format)
- Test: Add unit test for key validation

**Interfaces:**
- Consumes: `OPENAI_API_KEY` from env
- Produces: Validated key for LLM client

- [ ] **Step 1: Write failing test for key cleaning**

```python
# backend/tests/test_llm_planner.py::test_plan_with_llm_cleans_key
from unittest.mock import patch, MagicMock
from client.llm_planner import plan_with_llm
import os

def test_plan_with_llm_cleans_unicode_key():
    os.environ["OPENAI_API_KEY"] = "sk-test\u00f3key"  # contains ó
    os.environ["OPENAI_BASE_URL"] = "http://localhost:20128/v1"
    
    with patch("client.llm_planner.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"nome": "Test", "itens": []}'))]
        )
        
        result = plan_with_llm("test order")
        
        # Verify OpenAI was called with CLEANED key
        call_kwargs = mock_openai.call_args[1]
        assert "\u00f3" not in call_kwargs["api_key"]  # ó removed
```

- [ ] **Step 2: Run test - verify FAIL**
- [ ] **Step 3: Fix `plan_with_llm` to strip non-ASCII from key**
- [ ] **Step 4: Run test - verify PASS**
- [ ] **Step 5: Fix `.env` file - remove `ó` from key**
- [ ] **Step 6: Run ALL tests - verify GREEN**
- [ ] **Step 7: Commit**

---

### Task 2: Fix Streaming Capture (Cozinha Progress)

**Files:**
- Modify: `frontend/app/api/copilotkit/[...slug]/route.ts` (update `callA2AAgent`)
- Modify: `backend/server/executors/cozinha_executor.py` (ensure all steps in one response)
- Test: Add integration test for multi-message capture

**Interfaces:**
- Consumes: A2A JSON-RPC response with multiple message parts
- Produces: Concatenated string of ALL messages

- [ ] **Step 1: Write failing test for multi-message extraction**

```typescript
// frontend/__tests__/a2a-extract.test.ts
import { extractAllReplyText } from "@/app/api/copilotkit/[...slug]/route";

test("extractAllReplyText concatenates all message parts", () => {
  const response = {
    result: {
      message: {
        role: "ROLE_AGENT",
        parts: [
          { text: "🔥 Aquecendo o óleo..." },
          { text: "🥟 Massa sendo aberta..." },
          { text: "🍟 Fritando... golden & crispy!" }
        ]
      }
    }
  };
  
  const result = extractAllReplyText(response);
  expect(result).toContain("Aquecendo");
  expect(result).toContain("Massa");
  expect(result).toContain("Fritando");
});
```

- [ ] **Step 2: Run test - verify FAIL**
- [ ] **Step 3: Implement `extractAllReplyText` to join ALL parts with `\n`**
- [ ] **Step 4: Update `callA2AAgent` to use new extractor**
- [ ] **Step 5: Run test - verify PASS**
- [ ] **Step 6: Run ALL tests - verify GREEN**
- [ ] **Step 7: Commit**

---

### Task 3: Fix Timeline Sync (Keyword Detection)

**Files:**
- Modify: `frontend/components/Chat.tsx` (improve keyword detection)
- Test: Add unit tests for step detection from LLM responses

**Interfaces:**
- Consumes: LLM response text with agent mentions
- Produces: Correct `currentStep` number

- [ ] **Step 1: Write failing tests for edge cases**

```typescript
// frontend/__tests__/Chat.test.tsx
import { detectStep } from "@/components/Chat";

test("detectStep finds 'cozinha' in LLM response", () => {
  expect(detectStep("Agora vou chamar o agente cozinha")).toBe(2);
});

test("detectStep finds 'preparando' as cozinha", () => {
  expect(detectStep("O pastel está sendo preparado")).toBe(2);
});

test("detectStep prefers highest step", () => {
  expect(detectStep("fila e cozinha e entrega")).toBe(4); // entrega=4
});
```

- [ ] **Step 2: Run test - verify FAIL**
- [ ] **Step 3: Fix `detectStep` to handle compound messages, case-insensitive, word boundaries**
- [ ] **Step 4: Run test - verify PASS**
- [ ] **Step 5: Run ALL tests - verify GREEN**
- [ ] **Step 6: Commit**

---

### Task 4: Fix Docker Build Performance

**Files:**
- Modify: `frontend/Dockerfile` (optimize layers, add BuildKit)
- Modify: `docker-compose.yml` (add build args, cache mounts)

**Interfaces:**
- Produces: Fast, cached Docker build

- [ ] **Step 1: Measure current build time**
- [ ] **Step 2: Optimize Dockerfile (npm ci cache, next build cache)**
- [ ] **Step 3: Verify build completes in <5 min**
- [ ] **Step 4: Commit**

---

### Task 5: End-to-End Integration Test

**Files:**
- Create: `frontend/__tests__/e2e-chat.test.ts` (Playwright or integration)
- Test: Full flow from user message → LLM → tools → agents → timeline

**Interfaces:**
- Consumes: Running backend + frontend
- Produces: Verified working chat

- [ ] **Step 1: Start Docker stack**
- [ ] **Step 2: Write integration test (smoke test)**
- [ ] **Step 3: Verify test passes**
- [ ] **Step 4: Commit**

---

### Task 6: Safety Verification

**Files:** All
- [ ] Run ALL backend tests (51)
- [ ] Run ALL frontend tests (25)
- [ ] TypeScript clean
- [ ] Ruff clean
- [ ] Docker build + smoke test
- [ ] Commit all