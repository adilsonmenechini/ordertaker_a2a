import {
  CopilotRuntime,
  createCopilotRuntimeHandler,
  InMemoryAgentRunner,
} from "@copilotkit/runtime/v2";
import { HttpAgent } from "@ag-ui/client";
import { A2AMiddlewareAgent } from "@ag-ui/a2a-middleware";
import { NextRequest, NextResponse } from "next/server";

// ── Lazy-initialized runtime ────────────────────────────────────────
// Agent cards are fetched on first request, NOT at module load time.
// This prevents unhandled rejections when the backend isn't ready yet.

let runtimeInstance: CopilotRuntime | null = null;

function getRuntime(): CopilotRuntime {
  if (runtimeInstance) return runtimeInstance;

  const filaAgentUrl = process.env.FILA_AGENT_URL || "http://localhost:9001";
  const cozinhaAgentUrl =
    process.env.COZINHA_AGENT_URL || "http://localhost:9002";
  const preparoAgentUrl =
    process.env.PREPARO_AGENT_URL || "http://localhost:9003";
  const entregaAgentUrl =
    process.env.ENTREGA_AGENT_URL || "http://localhost:9004";
  const orchestratorUrl = process.env.ORCHESTRATOR_URL || "http://localhost:9001";

  const orchestrationAgent = new HttpAgent({ url: orchestratorUrl });

  const a2aMiddlewareAgent = new A2AMiddlewareAgent({
    description:
      "Pastelaria virtual com agentes especializados: Fila, Cozinha, Preparo e Entrega",
    agentUrls: [filaAgentUrl, cozinhaAgentUrl, preparoAgentUrl, entregaAgentUrl],
    orchestrationAgent,
    instructions: `
    Você é um atendente de pastelaria virtual. Gerencia pedidos de pastel usando agentes especializados.

    IMPRESCINDÍVEL: Logo no início da conversa, SEMPRE chame a tool 'mostrar_cardapio' para exibir o cardápio visual ao cliente antes de qualquer interação.

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
    - Responda sempre em português brasileiro
  `,
  });

  runtimeInstance = new CopilotRuntime({
    agents: {
      default: a2aMiddlewareAgent,
    },
    runner: new InMemoryAgentRunner(),
  });

  return runtimeInstance;
}

// ── Handler ─────────────────────────────────────────────────────────

const handler = createCopilotRuntimeHandler({
  // We pass a getter so runtime is created on first request, not at import
  get runtime() {
    return getRuntime();
  },
  basePath: "/api/copilotkit",
});

// CORS headers for external access
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}

export async function GET(request: NextRequest) {
  const response = await handler(request);
  Object.entries(corsHeaders).forEach(([key, value]) => {
    response.headers.set(key, value);
  });
  return response;
}

export async function POST(request: NextRequest) {
  const response = await handler(request);
  Object.entries(corsHeaders).forEach(([key, value]) => {
    response.headers.set(key, value);
  });
  return response;
}

export async function PATCH(request: NextRequest) {
  const response = await handler(request);
  Object.entries(corsHeaders).forEach(([key, value]) => {
    response.headers.set(key, value);
  });
  return response;
}

export async function DELETE(request: NextRequest) {
  const response = await handler(request);
  Object.entries(corsHeaders).forEach(([key, value]) => {
    response.headers.set(key, value);
  });
  return response;
}
