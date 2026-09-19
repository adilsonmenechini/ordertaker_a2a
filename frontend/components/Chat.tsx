"use client";

import React, { useState } from "react";
import { CopilotSidebar } from "@copilotkit/react-core/v2";
import { useFrontendTool } from "@copilotkit/react-core/v2";
import { Timeline } from "./Timeline";
import { MessageToA2A, MessageFromA2A } from "./A2AMessage";

const STEP_KEYWORDS: Record<string, number> = {
  pedido: 0,
  fila: 1,
  cozinha: 2,
  preparo: 3,
  entrega: 4,
  concluido: 4,
};

function detectStep(text: string): number {
  const lower = text.toLowerCase();
  for (const [keyword, step] of Object.entries(STEP_KEYWORDS)) {
    if (lower.includes(keyword)) return step;
  }
  return -1;
}

export function Chat() {
  const [currentStep, setCurrentStep] = useState(-1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  useFrontendTool({
    name: "send_message_to_a2a_agent",
    description: "Envia uma mensagem para um agente A2A",
    available: "frontend",
    parameters: [
      { name: "agentName", type: "string", description: "Nome do agente A2A" },
      { name: "task", type: "string", description: "Mensagem para o agente" },
    ],
    render: (props) => {
      const step = detectStep(props.args.task || "");
      if (step >= 0) {
        setCurrentStep(step);
        setCompletedSteps((prev) => {
          const newCompleted = [...prev];
          for (let i = 0; i < step; i++) {
            if (!newCompleted.includes(i)) newCompleted.push(i);
          }
          return newCompleted;
        });
      }

      return (
        <>
          <MessageToA2A {...props} />
          <MessageFromA2A {...props} />
        </>
      );
    },
  });

  return (
    <div className="flex h-screen">
      <div className="w-full max-w-2xl mx-auto flex flex-col">
        {/* Timeline */}
        <div className="border-b bg-white sticky top-0 z-10">
          <Timeline
            currentStep={currentStep}
            completedSteps={completedSteps}
          />
        </div>

        {/* Chat */}
        <div className="flex-1 overflow-hidden">
          <CopilotSidebar
            defaultOpen={true}
            labels={{
              title: "🥟 Pastelaria Virtual",
              initial:
                "Olá! Bem-vindo à Pastelaria Virtual! 🥟\n\nFaça seu pedido! Exemplo:\n- 2 pastéis de carne com borda de catupiry\n- 1 pastel de frango e 1 de queijo\n- Pastel de palmito sem cebola",
            }}
          />
        </div>
      </div>
    </div>
  );
}
