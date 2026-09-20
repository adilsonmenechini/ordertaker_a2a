"use client";

import React from "react";
import { ORDER_STEPS } from "./OrderState";

interface StateVisualizerProps {
  currentStep: number;
}

export function StateVisualizer({ currentStep }: StateVisualizerProps) {
  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h2
          className="text-lg font-semibold text-[var(--pv-brown)]"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          Andamento do Pedido
        </h2>
        <p className="text-sm text-[var(--pv-brown-light)] mt-0.5">
          Acompanhe cada etapa em tempo real
        </p>
      </div>

      {/* Steps */}
      <div className="relative pl-8">
        {/* Vertical line */}
        <div className="absolute left-[15px] top-3 bottom-3 w-[2px] bg-[#f0e6da]" />

        {/* Animated fill */}
        <div
          className="absolute left-[15px] top-3 w-[2px] rounded-full transition-all duration-700 ease-out"
          style={{
            height:
              currentStep < 0
                ? "0%"
                : `${(currentStep / (ORDER_STEPS.length - 1)) * 100}%`,
            background:
              "linear-gradient(180deg, var(--pv-green), var(--pv-amber))",
          }}
        />

        <div className="space-y-6">
          {ORDER_STEPS.map((step, idx) => {
            const isCompleted = idx < currentStep;
            const isCurrent = idx === currentStep;
            const isPending = idx > currentStep;

            return (
              <div key={step.key} className="relative flex items-start gap-4">
                {/* Circle */}
                <div
                  className={`
                    relative z-10 w-8 h-8 rounded-full flex items-center justify-center
                    text-xs font-semibold shrink-0 transition-all duration-500 ease-out
                    border-2
                    ${
                      isCompleted
                        ? "bg-[var(--pv-green)] border-[var(--pv-green)] text-white"
                        : ""
                    }
                    ${
                      isCurrent
                        ? "bg-[var(--pv-amber)] border-[var(--pv-amber)] text-white shadow-lg shadow-amber-200/50"
                        : ""
                    }
                    ${
                      isPending
                        ? "bg-white border-[#e0d5c8] text-[#b0a090]"
                        : ""
                    }
                  `}
                >
                  {isCompleted ? (
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={3}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  ) : (
                    <span>{idx + 1}</span>
                  )}

                  {/* Active pulse */}
                  {isCurrent && (
                    <span className="absolute inset-0 rounded-full animate-ping bg-[var(--pv-amber)] opacity-30" />
                  )}
                </div>

                {/* Text */}
                <div className="pt-0.5 min-w-0">
                  <h4
                    className={`
                      text-sm font-medium transition-colors duration-300
                      ${isCompleted || isCurrent ? "text-[var(--pv-brown)]" : "text-[#b0a090]"}
                    `}
                  >
                    {step.label}
                  </h4>
                  <p
                    className={`
                      text-xs mt-0.5 transition-colors duration-300
                      ${isCurrent ? "text-[var(--pv-amber-dark)]" : "text-[#c0b0a0]"}
                    `}
                  >
                    {isCompleted ? "Concluído" : step.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Status message */}
      {currentStep >= 0 && (
        <div className="bg-[var(--pv-cream)] rounded-xl p-4 border border-[#f0e6da]">
          <div className="flex items-center gap-2">
            {currentStep >= ORDER_STEPS.length - 1 ? (
              <>
                <span className="text-lg">✅</span>
                <span className="text-sm font-medium text-[var(--pv-green-dark)]">
                  Pedido pronto! Pode retirar.
                </span>
              </>
            ) : (
              <>
                <span className="text-lg">⏳</span>
                <span className="text-sm text-[var(--pv-brown-light)]">
                  {ORDER_STEPS[currentStep]?.desc}...
                </span>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
