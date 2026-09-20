import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { StateVisualizer } from "@/components/StateVisualizer";

describe("StateVisualizer", () => {
  it("renders all 5 steps", () => {
    render(<StateVisualizer currentStep={-1} />);
    expect(screen.getByText("Pedido")).toBeInTheDocument();
    expect(screen.getByText("Fila")).toBeInTheDocument();
    expect(screen.getByText("Cozinha")).toBeInTheDocument();
    expect(screen.getByText("Preparo")).toBeInTheDocument();
    expect(screen.getByText("Entrega")).toBeInTheDocument();
  });

  it("shows header text", () => {
    render(<StateVisualizer currentStep={-1} />);
    expect(screen.getByText("Andamento do Pedido")).toBeInTheDocument();
    expect(
      screen.getByText("Acompanhe cada etapa em tempo real"),
    ).toBeInTheDocument();
  });

  it("shows pending description when step is -1", () => {
    render(<StateVisualizer currentStep={-1} />);
    expect(screen.getByText("Recebendo seu pedido")).toBeInTheDocument();
  });

  it("shows completed for past steps", () => {
    render(<StateVisualizer currentStep={2} />);
    const completedTexts = screen.getAllByText("Concluído");
    expect(completedTexts.length).toBe(2); // pedido + fila
  });

  it("shows delivery message at final step", () => {
    render(<StateVisualizer currentStep={4} />);
    expect(screen.getByText("Pedido pronto! Pode retirar.")).toBeInTheDocument();
  });
});
