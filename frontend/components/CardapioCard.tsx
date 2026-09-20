"use client";

import React from "react";

const SABORES = [
  { name: "Carne", emoji: "🥩" },
  { name: "Frango", emoji: "🍗" },
  { name: "Queijo", emoji: "🧀" },
  { name: "Palmito", emoji: "🌱" },
  { name: "Carne c/ Queijo", emoji: "🥩🧀" },
];

const BORDAS = ["Normal", "Catupiry", "Queijo"];

const EXEMPLOS = [
  "2 pastéis de carne com borda de catupiry",
  "1 pastel de frango e 1 de queijo",
  "Pastel de palmito, borda normal",
];

export function CardapioCard() {
  return (
    <div className="px-1 py-2 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-xl">🥟</span>
        <h3
          className="text-base font-semibold text-[var(--pv-brown)]"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          Cardápio
        </h3>
      </div>

      {/* Sabores */}
      <div className="bg-white rounded-xl p-4 border border-[#f0e6da] shadow-sm">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--pv-brown-light)] mb-3">
          Sabores
        </h4>
        <div className="grid grid-cols-3 gap-2">
          {SABORES.map((sabor) => (
            <div
              key={sabor.name}
              className="flex flex-col items-center gap-1 bg-[var(--pv-cream)] rounded-lg px-2 py-3"
            >
              <span className="text-2xl">{sabor.emoji}</span>
              <span className="text-xs font-medium text-[var(--pv-brown)] text-center leading-tight">
                {sabor.name}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Bordas */}
      <div className="bg-white rounded-xl p-4 border border-[#f0e6da] shadow-sm">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--pv-brown-light)] mb-3">
          Bordas
        </h4>
        <div className="flex gap-2">
          {BORDAS.map((borda) => (
            <span
              key={borda}
              className="px-3 py-1.5 bg-[var(--pv-pink)] text-[var(--pv-brown)] rounded-full text-xs font-medium"
            >
              {borda}
            </span>
          ))}
        </div>
      </div>

      {/* Exemplos */}
      <div className="bg-white rounded-xl p-4 border border-[#f0e6da] shadow-sm">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--pv-brown-light)] mb-3">
          Como pedir
        </h4>
        <div className="space-y-2">
          {EXEMPLOS.map((exemplo) => (
            <p
              key={exemplo}
              className="text-xs text-[var(--pv-brown-light)] pl-3 border-l-2 border-[var(--pv-amber)]/30"
            >
              {exemplo}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}
