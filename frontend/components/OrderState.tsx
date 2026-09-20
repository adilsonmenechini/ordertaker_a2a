"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";

export interface OrderItem {
  sabor: string;
  quantidade: number;
  borda: string;
}

export interface OrderState {
  items: OrderItem[];
  status: string;
  cliente: string;
}

interface OrderContextValue {
  order: OrderState;
  currentStep: number;
  setOrder: (order: OrderState) => void;
  setCurrentStep: (step: number) => void;
}

const ORDER_STEPS = [
  { key: "pedido", label: "Pedido", desc: "Recebendo seu pedido" },
  { key: "fila", label: "Fila", desc: "Na fila de espera" },
  { key: "cozinha", label: "Cozinha", desc: "Preparando na friadeira" },
  { key: "preparo", label: "Preparo", desc: "Embalando com carinho" },
  { key: "entrega", label: "Entrega", desc: "Pronto para retirada" },
];

const defaultOrder: OrderState = {
  items: [],
  status: "aguardando",
  cliente: "",
};

const OrderContext = createContext<OrderContextValue | null>(null);

export function OrderStateProvider({ children }: { children: ReactNode }) {
  const [order, setOrder] = useState<OrderState>(defaultOrder);
  const [currentStep, setCurrentStep] = useState(-1);

  return (
    <OrderContext.Provider value={{ order, currentStep, setOrder, setCurrentStep }}>
      {children}
    </OrderContext.Provider>
  );
}

export function useOrderState() {
  const ctx = useContext(OrderContext);
  if (!ctx) throw new Error("useOrderState must be used within OrderStateProvider");
  return ctx;
}

export { ORDER_STEPS };
