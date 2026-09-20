"use client";

import React from "react";
import { OrderState } from "./OrderState";

const SABOR_EMOJI: Record<string, string> = {
  carne: "🥩",
  frango: "🍗",
  queijo: "🧀",
  palmito: "🌱",
  carne_com_queijo: "🥩🧀",
};

interface OrderDetailsProps {
  order: OrderState;
}

export function OrderDetails({ order }: OrderDetailsProps) {
  const hasItems = order.items.length > 0;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h2
          className="text-lg font-semibold text-[var(--pv-brown)]"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          Seu Pedido
        </h2>
        <p className="text-sm text-[var(--pv-brown-light)] mt-0.5">
          {hasItems ? "Detalhes do pedido atual" : "Faça seu pedido no chat ao lado"}
        </p>
      </div>

      {!hasItems ? (
        /* Empty state */
        <div className="flex flex-col items-center text-center py-10">
          <div className="w-16 h-16 rounded-full bg-[var(--pv-cream)] flex items-center justify-center mb-4">
            <span className="text-3xl">🥟</span>
          </div>
          <h3 className="text-[var(--pv-brown)] font-medium mb-1">
            Nenhum pedido ainda
          </h3>
          <p className="text-sm text-[var(--pv-brown-light)] max-w-[220px]">
            Peça seu pastel pelo chat e os detalhes aparecerão aqui.
          </p>
        </div>
      ) : (
        <>
          {/* Order items */}
          <div className="space-y-3">
            {order.items.map((item, idx) => (
              <div
                key={idx}
                className="bg-[var(--pv-cream)] rounded-xl p-4 border border-[#f0e6da]"
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl mt-0.5">
                    {SABOR_EMOJI[item.sabor] || "🥟"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-[var(--pv-brown)] capitalize">
                        {item.sabor.replace(/_/g, " ")}
                      </h4>
                      <span className="text-sm font-semibold text-[var(--pv-amber)]">
                        x{item.quantidade}
                      </span>
                    </div>
                    <p className="text-sm text-[var(--pv-brown-light)] mt-1">
                      Borda: <span className="capitalize">{item.borda}</span>
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="bg-white rounded-xl p-4 border border-[#f0e6da]">
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--pv-brown-light)]">Total de pastéis</span>
              <span className="font-semibold text-[var(--pv-brown)]">
                {order.items.reduce((sum, item) => sum + item.quantidade, 0)}
              </span>
            </div>
            {order.cliente && (
              <div className="flex items-center justify-between text-sm mt-2 pt-2 border-t border-[#f0e6da]">
                <span className="text-[var(--pv-brown-light)]">Cliente</span>
                <span className="text-[var(--pv-brown)]">{order.cliente}</span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
