"use client";

import React from "react";

const STEPS = [
  { key: "pedido", label: "Pedido", icon: "📋", color: "blue" },
  { key: "fila", label: "Fila", icon: "📍", color: "yellow" },
  { key: "cozinha", label: "Cozinha", icon: "🍳", color: "orange" },
  { key: "preparo", label: "Preparo", icon: "📦", color: "purple" },
  { key: "entrega", label: "Entrega", icon: "🚚", color: "green" },
] as const;

interface TimelineProps {
  currentStep: number;
  completedSteps: number[];
}

const colorMap: Record<string, { bg: string; text: string; border: string }> = {
  blue: { bg: "bg-blue-100", text: "text-blue-700", border: "border-blue-400" },
  yellow: { bg: "bg-yellow-100", text: "text-yellow-700", border: "border-yellow-400" },
  orange: { bg: "bg-orange-100", text: "text-orange-700", border: "border-orange-400" },
  purple: { bg: "bg-purple-100", text: "text-purple-700", border: "border-purple-400" },
  green: { bg: "bg-green-100", text: "text-green-700", border: "border-green-400" },
};

export function Timeline({ currentStep, completedSteps }: TimelineProps) {
  return (
    <div className="w-full p-4">
      <h3 className="text-lg font-bold mb-4 text-center">🥟 Status do Pedido</h3>
      <div className="flex items-center justify-between relative">
        {/* Connector line */}
        <div className="absolute top-6 left-0 right-0 h-1 bg-gray-200 z-0" />
        <div
          className="absolute top-6 left-0 h-1 bg-green-500 z-10 transition-all duration-500"
          style={{ width: `${(completedSteps.length / (STEPS.length - 1)) * 100}%` }}
        />

        {STEPS.map((step, idx) => {
          const isCompleted = completedSteps.includes(idx);
          const isCurrent = currentStep === idx;
          const colors = colorMap[step.color];

          return (
            <div key={step.key} className="flex flex-col items-center relative z-20">
              <div
                className={`
                  w-12 h-12 rounded-full flex items-center justify-center text-xl
                  border-2 transition-all duration-300
                  ${isCompleted ? "bg-green-500 border-green-500 text-white" : ""}
                  ${isCurrent ? `${colors.bg} ${colors.border} ${colors.text} animate-pulse` : ""}
                  ${!isCompleted && !isCurrent ? "bg-gray-100 border-gray-300 text-gray-400" : ""}
                `}
              >
                {isCompleted ? "✓" : step.icon}
              </div>
              <span
                className={`
                  mt-2 text-xs font-medium
                  ${isCompleted || isCurrent ? "text-gray-900" : "text-gray-400"}
                `}
              >
                {step.label}
              </span>
              {isCurrent && (
                <span className="text-[10px] text-gray-500 animate-pulse">atual</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
