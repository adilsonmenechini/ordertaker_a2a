"use client";

import React, { useEffect, useRef } from "react";
import { useCopilotChatHeadless_c, useCopilotAction } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";
import { useOrderState } from "./OrderState";
import { CardapioCard } from "./CardapioCard";

const STEP_KEYWORDS: Record<string, number> = {
  pedido: 0,
  fila: 1,
  cozinha: 2,
  preparo: 3,
  entrega: 4,
  concluido: 4,
  entregue: 4,
  pronto: 3,
  embalando: 3,
  fritando: 2,
  preparando: 2,
};

function detectStep(text: string): number {
  const lower = text.toLowerCase();
  for (const [keyword, step] of Object.entries(STEP_KEYWORDS)) {
    if (lower.includes(keyword)) return step;
  }
  return -1;
}

interface ChatProps {
  className?: string;
}

export function Chat({ className }: ChatProps) {
  const lastMessageCount = useRef(0);
  const { messages } = useCopilotChatHeadless_c();
  const { setCurrentStep } = useOrderState();

  // Register the cardápio tool — renders visual card in chat
  useCopilotAction({
    name: "mostrar_cardapio",
    description: "Mostra o cardápio completo da pastelaria com sabores, bordas e exemplos de pedido",
    parameters: [],
    handler: async () => {
      // The render function handles the visual output
    },
    render: () => <CardapioCard />,
  });

  // Track messages and update timeline step
  useEffect(() => {
    if (!messages || messages.length === lastMessageCount.current) return;
    lastMessageCount.current = messages.length;

    let maxStep = -1;
    for (const msg of messages) {
      const text =
        typeof msg.content === "string"
          ? msg.content
          : Array.isArray(msg.content)
            ? msg.content
                .filter((p: { type: string }) => p.type === "text")
                .map((p: { text: string }) => p.text)
                .join(" ")
            : "";

      const step = detectStep(text);
      if (step > maxStep) maxStep = step;
    }

    if (maxStep >= 0) {
      setCurrentStep(maxStep);
    }
  }, [messages, setCurrentStep]);

  return (
    <div className={className}>
      <CopilotChat
        className="h-full w-full"
        instructions={`Você é um atendente de pastelaria virtual. Gerencia pedidos de pastel usando agentes especializados.

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
- Responda sempre em português brasileiro`}
        labels={{
          placeholder: "Faça seu pedido de pastel... 🥟",
          initial: "Olá! 🥟 Bem-vindo à Pastelaria Virtual! Como posso te ajudar?",
        }}
      />
    </div>
  );
}
