import {
  CopilotRuntime,
  createCopilotRuntimeHandler,
  InMemoryAgentRunner,
} from "@copilotkit/runtime/v2";
import { HttpAgent } from "@ag-ui/client";
import { A2AMiddlewareAgent } from "@ag-ui/a2a-middleware";
import { NextRequest, NextResponse } from "next/server";

// ── Lazy runtime — created on first request, not at import ──────────

let runtimeReady: Promise<CopilotRuntime> | null = null;

function ensureRuntime(): Promise<CopilotRuntime> {
  if (runtimeReady) return runtimeReady;

  runtimeReady = (async () => {
    const filaUrl = process.env.FILA_AGENT_URL || "http://localhost:9001";
    const cozinhaUrl = process.env.COZINHA_AGENT_URL || "http://localhost:9002";
    const preparoUrl = process.env.PREPARO_AGENT_URL || "http://localhost:9003";
    const entregaUrl = process.env.ENTREGA_AGENT_URL || "http://localhost:9004";
    const orchUrl = process.env.ORCHESTRATOR_URL || "http://localhost:9001";

    const agent = new A2AMiddlewareAgent({
      description:
        "Pastelaria virtual com agentes especializados: Fila, Cozinha, Preparo e Entrega",
      agentUrls: [filaUrl, cozinhaUrl, preparoUrl, entregaUrl],
      orchestrationAgent: new HttpAgent({ url: orchUrl }),
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

    return new CopilotRuntime({
      agents: { default: agent },
      runner: new InMemoryAgentRunner(),
    });
  })();

  return runtimeReady;
}

// ── Single handler instance, lazily wired ───────────────────────────

const corsHeaders: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

let cachedHandler: ((request: NextRequest) => Promise<Response>) | null = null;

async function getHandler() {
  if (cachedHandler) return cachedHandler;

  const runtime = await ensureRuntime();
  cachedHandler = createCopilotRuntimeHandler({
    runtime,
    basePath: "/api/copilotkit",
  });
  return cachedHandler;
}

// ── Route handlers ──────────────────────────────────────────────────

async function handleRequest(request: NextRequest): Promise<Response> {
  try {
    const handler = await getHandler();
    console.log("[CopilotKit]", request.method, request.nextUrl.pathname);
    const response = await handler(request);
    for (const [k, v] of Object.entries(corsHeaders)) {
      response.headers.set(k, v);
    }
    return response;
  } catch (err) {
    console.error("[CopilotKit] Request error:", err);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}

export const GET = handleRequest;
export const POST = handleRequest;
export const PATCH = handleRequest;
export const DELETE = handleRequest;
