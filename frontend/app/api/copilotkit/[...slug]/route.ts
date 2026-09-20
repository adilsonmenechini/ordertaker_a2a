import {
  CopilotRuntime,
  createCopilotRuntimeHandler,
  InMemoryAgentRunner,
  defineTool,
} from "@copilotkit/runtime/v2";
import { z } from "zod";
import { NextRequest, NextResponse } from "next/server";

// ── A2A backend helpers ─────────────────────────────────────────────

const A2A_HEADERS: Record<string, string> = {
  "A2A-Version": "1.0",
  "Content-Type": "application/json",
};

function getAgentUrl(agent: string): string {
  const envKey = `${agent.toUpperCase()}_AGENT_URL`;
  return process.env[envKey] || `http://localhost:${9001 + ["fila", "cozinha", "preparo", "entrega"].indexOf(agent)}`;
}

function extractReplyText(result: Record<string, unknown>): string {
  const task = (result.task || result) as Record<string, unknown>;
  const artifacts = (task.artifacts || []) as Array<Record<string, unknown>>;
  for (const artifact of artifacts) {
    const parts = (artifact.parts || []) as Array<Record<string, unknown>>;
    for (const part of parts) {
      if (part.text && typeof part.text === "string") return part.text;
    }
  }
  const status = (task.status || {}) as Record<string, unknown>;
  const msg = (status.message || {}) as Record<string, unknown>;
  const msgParts = (msg.parts || []) as Array<Record<string, unknown>>;
  for (const part of msgParts) {
    if (part.text && typeof part.text === "string") return part.text;
  }
  return JSON.stringify(result).slice(0, 300);
}

async function callA2AAgent(
  agent: string,
  text: string,
): Promise<string> {
  const baseUrl = getAgentUrl(agent);
  const jsonrpcUrl = `${baseUrl}/a2a/jsonrpc`;
  const payload = {
    jsonrpc: "2.0",
    id: crypto.randomUUID(),
    method: "SendMessage",
    params: {
      message: {
        role: 1,
        message_id: crypto.randomUUID(),
        parts: [{ text }],
      },
    },
  };

  console.log(`[A2A] Calling ${agent} at ${jsonrpcUrl}`);
  const resp = await fetch(jsonrpcUrl, {
    method: "POST",
    headers: A2A_HEADERS,
    body: JSON.stringify(payload),
  });
  const body = await resp.json();
  if (body.error) throw new Error(`A2A ${agent} error: ${JSON.stringify(body.error)}`);
  const result = body.result || {};
  return extractReplyText(result);
}

// ── LLM-powered orchestrator agent ──────────────────────────────────

const SYSTEM_PROMPT = `Você é o atendente virtual da Pastelaria "Sabor da Terra".
Gerencia pedidos de pastel usando agentes especializados.

IMPRESCINDÍVEL: Logo no início da conversa, SEMPRE chame a tool 'mostrar_cardapio' para exibir o cardápio visual ao cliente antes de qualquer interação.

FLUXO DO PEDIDO (chame as tools na ordem correta):
1. agente_fila — Recebe o pedido e posiciona na fila ( SEMPRE primeiro )
2. agente_cozinha — Prepara o pastel na fritadeira (com streaming)
3. agente_preparo — Embala o pedido
4. agente_entrega — Entrega ao cliente

SABORES: carne, frango, queijo, palmito, carne_com_queijo
BORDAS: normal, queijo, catupiry
QUANTIDADES: 1, 2, 3, 4, 5+

REGRAS:
- Chame as tools UM POR VEZ, espere o resultado antes de chamar a próxima
- Passe as informações do resultado anterior como contexto para o próximo agente
- Use agente_fila PRIMEIRO para registrar o pedido
- Depois agente_cozinha, agente_preparo e agente_entrega em sequência
- Ao final, confirme a entrega ao cliente
- Responda sempre em português brasileiro, com empatia e simpatia
- Se o cliente pedir para ver o cardápio, chame mostrar_cardapio`;

const filaTool = defineTool({
  name: "agente_fila",
  description:
    "Recebe o pedido do cliente e o posiciona na fila de preparação. Use esta tool PRIMEIRO para registrar o pedido antes de enviar para a cozinha.",
  parameters: z.object({
    pedido: z
      .string()
      .describe(
        "Descrição do pedido: sabores, quantidades e bordas. Ex: '2 pastéis de carne com borda de queijo, 1 pastel de frango'",
      ),
    nome_cliente: z.string().describe("Nome do cliente"),
  }),
  execute: async ({ pedido, nome_cliente }) => {
    const text = `Novo pedido de ${nome_cliente}: ${pedido}`;
    const reply = await callA2AAgent("fila", text);
    return { resultado_fila: reply };
  },
});

const cozinhaTool = defineTool({
  name: "agente_cozinha",
  description:
    "Prepara o(s) pastel(is) na fritadeira com óleo quente. Mostra o progresso do preparo. Use SOMENTE DEPOIS que o agente_fila já processou o pedido.",
  parameters: z.object({
    pedido: z
      .string()
      .describe("Descrição do pedido recebido da fila"),
    nome_cliente: z.string().describe("Nome do cliente"),
  }),
  execute: async ({ pedido, nome_cliente }) => {
    const text = `Preparar pedido de ${nome_cliente}: ${pedido}`;
    const reply = await callA2AAgent("cozinha", text);
    return { resultado_cozinha: reply };
  },
});

const preparoTool = defineTool({
  name: "agente_preparo",
  description:
    "Embala o(s) pastel(is) preparados e separa para entrega. Use SOMENTE DEPOIS que o agente_cozinha já finalizou o preparo.",
  parameters: z.object({
    pedido: z
      .string()
      .describe("Descrição do pedido já preparado na cozinha"),
    nome_cliente: z.string().describe("Nome do cliente"),
  }),
  execute: async ({ pedido, nome_cliente }) => {
    const text = `Embalar pedido de ${nome_cliente}: ${pedido}`;
    const reply = await callA2AAgent("preparo", text);
    return { resultado_preparo: reply };
  },
});

const entregaTool = defineTool({
  name: "agente_entrega",
  description:
    "Realiza a entrega do pedido embalado ao cliente. Use SOMENTE DEPOIS que o agente_preparo já embalou o pedido.",
  parameters: z.object({
    pedido: z
      .string()
      .describe("Descrição do pedido já embalado"),
    nome_cliente: z.string().describe("Nome do cliente"),
  }),
  execute: async ({ pedido, nome_cliente }) => {
    const text = `Entregar pedido de ${nome_cliente}: ${pedido}`;
    const reply = await callA2AAgent("entrega", text);
    return { resultado_entrega: reply };
  },
});

// ── Lazy runtime — created on first request ─────────────────────────

let runtimeReady: Promise<CopilotRuntime> | null = null;

function ensureRuntime(): Promise<CopilotRuntime> {
  if (runtimeReady) return runtimeReady;

  runtimeReady = (async () => {
    const { createOpenAI } = await import("@ai-sdk/openai");

    // Resolve model: if LLM_MODEL has no recognized prefix, use openai provider
    // (user may set custom OPENAI_BASE_URL for OpenRouter/proxy)
    const rawModel = process.env.LLM_MODEL || "openai/gpt-4o-mini";
    const knownProviders = ["openai/", "anthropic/", "google/", "gemini/", "minimax/", "vertex/"];
    const hasProvider = knownProviders.some((p) => rawModel.startsWith(p));

    const apiKey = process.env.OPENAI_API_KEY || "";
    const baseURL = process.env.OPENAI_BASE_URL;
    const provider = createOpenAI({ apiKey, ...(baseURL ? { baseURL } : {}) });
    const modelName = hasProvider ? rawModel.split("/").slice(1).join("/") : rawModel;

    console.log(`[CopilotKit] LLM model: ${modelName}, baseURL: ${baseURL || "(default)"}`);

    const agent = new (await import("@copilotkit/runtime/v2")).BuiltInAgent({
      model: provider(modelName),
      prompt: SYSTEM_PROMPT,
      tools: [filaTool, cozinhaTool, preparoTool, entregaTool],
      maxSteps: 6,
    });

    return new CopilotRuntime({
      agents: { default: agent },
      runner: new InMemoryAgentRunner(),
    });
  })();

  return runtimeReady;
}

// ── Single cached handler ───────────────────────────────────────────

const corsHeaders: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

let cachedHandler: ((request: Request) => Promise<Response>) | null = null;

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
    console.log("[CopilotKit]", request.method, request.nextUrl.pathname);
    const handler = await getHandler();
    const response = await handler(request);
    for (const [k, v] of Object.entries(corsHeaders)) {
      response.headers.set(k, v);
    }
    return response;
  } catch (err) {
    console.error("[CopilotKit] Request error:", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal error" },
      { status: 500 },
    );
  }
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}

export const GET = handleRequest;
export const POST = handleRequest;
export const PATCH = handleRequest;
export const DELETE = handleRequest;
