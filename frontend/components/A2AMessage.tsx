"use client";

import React from "react";

type MessageActionRenderProps = {
  status: string;
  args: {
    agentName?: string;
    task?: string;
  };
};

const agentStyles: Record<string, { icon: string; bgColor: string; textColor: string; borderColor: string }> = {
  "Pastel Fila Agent": { icon: "📋", bgColor: "bg-yellow-50", textColor: "text-yellow-700", borderColor: "border-yellow-300" },
  "Pastel Cozinha Agent": { icon: "🍳", bgColor: "bg-orange-50", textColor: "text-orange-700", borderColor: "border-orange-300" },
  "Pastel Preparo Agent": { icon: "📦", bgColor: "bg-purple-50", textColor: "text-purple-700", borderColor: "border-purple-300" },
  "Pastel Entrega Agent": { icon: "🚚", bgColor: "bg-green-50", textColor: "text-green-700", borderColor: "border-green-300" },
};

function getAgentStyle(name: string) {
  return agentStyles[name] || { icon: "🤖", bgColor: "bg-gray-50", textColor: "text-gray-700", borderColor: "border-gray-300" };
}

function truncateTask(task: string, maxLen = 80) {
  return task.length > maxLen ? task.slice(0, maxLen) + "..." : task;
}

export function MessageToA2A({ status, args }: MessageActionRenderProps) {
  switch (status) {
    case "executing":
    case "complete":
      break;
    default:
      return null;
  }

  if (!args.agentName || !args.task) return null;

  const style = getAgentStyle(args.agentName);

  return (
    <div className={`${style.bgColor} border ${style.borderColor} rounded-lg px-4 py-3 my-2`}>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-gray-700 text-white">
            Orquestrador
          </span>
          <span className="text-gray-400 text-sm">→</span>
          <span className={`px-3 py-1 rounded-full text-xs font-semibold border-2 ${style.bgColor} ${style.textColor} ${style.borderColor}`}>
            {style.icon} {args.agentName}
          </span>
        </div>
        <span className="text-gray-700 text-sm flex-1">{truncateTask(args.task)}</span>
      </div>
    </div>
  );
}

export function MessageFromA2A({ status, args }: MessageActionRenderProps) {
  if (status !== "complete" || !args.agentName) return null;

  const style = getAgentStyle(args.agentName);

  return (
    <div className="my-2">
      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full text-xs font-semibold border-2 ${style.bgColor} ${style.textColor} ${style.borderColor}`}>
            {style.icon} {args.agentName}
          </span>
          <span className="text-gray-400 text-sm">→</span>
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-gray-700 text-white">
            Orquestrador
          </span>
          <span className="text-xs text-green-600">✓ Resposta recebida</span>
        </div>
      </div>
    </div>
  );
}
