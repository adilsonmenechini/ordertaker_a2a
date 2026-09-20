import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CardapioCard } from "@/components/CardapioCard";

describe("CardapioCard", () => {
  it("renders all 5 sabores", () => {
    render(<CardapioCard />);
    expect(screen.getByText("Carne")).toBeInTheDocument();
    expect(screen.getByText("Frango")).toBeInTheDocument();
    expect(screen.getAllByText("Queijo").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Palmito")).toBeInTheDocument();
    expect(screen.getByText("Carne c/ Queijo")).toBeInTheDocument();
  });

  it("renders all 3 bordas", () => {
    render(<CardapioCard />);
    expect(screen.getByText("Normal")).toBeInTheDocument();
    expect(screen.getByText("Catupiry")).toBeInTheDocument();
    expect(screen.getAllByText("Queijo").length).toBeGreaterThanOrEqual(2);
  });

  it("renders 3 order examples", () => {
    render(<CardapioCard />);
    expect(
      screen.getByText("2 pastéis de carne com borda de catupiry"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("1 pastel de frango e 1 de queijo"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Pastel de palmito, borda normal"),
    ).toBeInTheDocument();
  });

  it("renders the cardápio title", () => {
    render(<CardapioCard />);
    expect(screen.getByText(/Cardápio/)).toBeInTheDocument();
  });
});
