import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { OrderDetails } from "@/components/OrderDetails";
import { OrderState } from "@/components/OrderState";

const emptyOrder: OrderState = { items: [], status: "aguardando", cliente: "" };

const orderWithItems: OrderState = {
  items: [
    { sabor: "carne", quantidade: 2, borda: "catupiry" },
    { sabor: "frango", quantidade: 1, borda: "normal" },
  ],
  status: "cozinha",
  cliente: "Maria",
};

describe("OrderDetails", () => {
  it("shows empty state when no items", () => {
    render(<OrderDetails order={emptyOrder} />);
    expect(screen.getByText("Nenhum pedido ainda")).toBeInTheDocument();
    expect(
      screen.getByText("Peça seu pastel pelo chat e os detalhes aparecerão aqui."),
    ).toBeInTheDocument();
  });

  it("renders header", () => {
    render(<OrderDetails order={emptyOrder} />);
    expect(screen.getByText("Seu Pedido")).toBeInTheDocument();
  });

  it("renders order items", () => {
    render(<OrderDetails order={orderWithItems} />);
    expect(screen.getByText("carne")).toBeInTheDocument();
    expect(screen.getByText("frango")).toBeInTheDocument();
  });

  it("shows quantities", () => {
    render(<OrderDetails order={orderWithItems} />);
    expect(screen.getByText("x2")).toBeInTheDocument();
    expect(screen.getByText("x1")).toBeInTheDocument();
  });

  it("shows borda", () => {
    render(<OrderDetails order={orderWithItems} />);
    // CSS capitalize class handles visual capitalization
    expect(screen.getByText("catupiry")).toBeInTheDocument();
    expect(screen.getByText("normal")).toBeInTheDocument();
  });

  it("shows total pastel count", () => {
    render(<OrderDetails order={orderWithItems} />);
    expect(screen.getByText("3")).toBeInTheDocument(); // 2 + 1
  });

  it("shows client name", () => {
    render(<OrderDetails order={orderWithItems} />);
    expect(screen.getByText("Maria")).toBeInTheDocument();
  });
});
