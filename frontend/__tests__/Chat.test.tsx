import { describe, it, expect } from "vitest";
import { detectStep } from "@/components/Chat";

describe("detectStep", () => {
  it("finds 'pedido' keyword", () => {
    expect(detectStep("Pedido recebido")).toBe(0);
  });

  it("finds 'fila' keyword", () => {
    expect(detectStep("Posição na fila")).toBe(1);
  });

  it("finds 'cozinha' keyword", () => {
    expect(detectStep("Agora vou chamar o agente cozinha")).toBe(2);
  });

  it("finds 'preparo' keyword", () => {
    expect(detectStep("Encaminhando para o preparo")).toBe(3);
  });

  it("finds 'entrega' keyword", () => {
    expect(detectStep("Saiu para entrega")).toBe(4);
  });

  it("finds 'concluido' keyword", () => {
    expect(detectStep("Pedido concluido")).toBe(4);
  });

  it("finds 'entregue' keyword", () => {
    expect(detectStep("O pedido foi entregue")).toBe(4);
  });

  it("finds synonyms: 'pronto' -> preparo", () => {
    expect(detectStep("O pastel está pronto")).toBe(3);
  });

  it("finds synonyms: 'embalando' -> preparo", () => {
    expect(detectStep("Embalando o pedido")).toBe(3);
  });

  it("finds synonyms: 'fritando' -> cozinha", () => {
    expect(detectStep("Fritando o pastel")).toBe(2);
  });

  it("finds synonyms: 'preparando' -> cozinha", () => {
    expect(detectStep("Preparando na cozinha")).toBe(2);
  });

  it("is case-insensitive", () => {
    expect(detectStep("COZINHA")).toBe(2);
    expect(detectStep("Entrega")).toBe(4);
  });

  it("returns highest step when multiple keywords present", () => {
    expect(detectStep("fila e cozinha e entrega")).toBe(4); // entrega=4 highest
    expect(detectStep("pedido cozinha")).toBe(2); // cozinha=2 > pedido=0
  });

  it("returns -1 for unknown text", () => {
    expect(detectStep("Olá, como vai?")).toBe(-1);
    expect(detectStep("")).toBe(-1);
  });

  it("matches whole words only (no partial matches)", () => {
    expect(detectStep("preparando")).toBe(2); // contains "preparando"
    // "preparacao" should NOT match "preparo" 
    expect(detectStep("preparacao")).toBe(-1);
  });
});