import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import {
  OrderStateProvider,
  useOrderState,
  ORDER_STEPS,
} from "@/components/OrderState";

// Helper component that reads context
function TestConsumer() {
  const { order, currentStep, setOrder, setCurrentStep } = useOrderState();
  return (
    <div>
      <span data-testid="status">{order.status}</span>
      <span data-testid="step">{currentStep}</span>
      <span data-testid="items-count">{order.items.length}</span>
      <button onClick={() => setCurrentStep(2)}>Go to cozinha</button>
      <button
        onClick={() =>
          setOrder({
            items: [{ sabor: "carne", quantidade: 2, borda: "catupiry" }],
            status: "pedido",
            cliente: "Maria",
          })
        }
      >
        Set order
      </button>
    </div>
  );
}

describe("OrderState", () => {
  it("provides default state", () => {
    render(
      <OrderStateProvider>
        <TestConsumer />
      </OrderStateProvider>,
    );
    expect(screen.getByTestId("status").textContent).toBe("aguardando");
    expect(screen.getByTestId("step").textContent).toBe("-1");
    expect(screen.getByTestId("items-count").textContent).toBe("0");
  });

  it("updates currentStep via setCurrentStep", () => {
    render(
      <OrderStateProvider>
        <TestConsumer />
      </OrderStateProvider>,
    );
    fireEvent.click(screen.getByText("Go to cozinha"));
    expect(screen.getByTestId("step").textContent).toBe("2");
  });

  it("updates order via setOrder", () => {
    render(
      <OrderStateProvider>
        <TestConsumer />
      </OrderStateProvider>,
    );
    fireEvent.click(screen.getByText("Set order"));
    expect(screen.getByTestId("items-count").textContent).toBe("1");
    expect(screen.getByTestId("status").textContent).toBe("pedido");
  });

  it("throws when used outside provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    function BadConsumer() {
      useOrderState();
      return null;
    }
    expect(() => render(<BadConsumer />)).toThrow(
      "useOrderState must be used within OrderStateProvider",
    );
    spy.mockRestore();
  });

  it("exports ORDER_STEPS with 5 entries", () => {
    expect(ORDER_STEPS).toHaveLength(5);
    expect(ORDER_STEPS[0].key).toBe("pedido");
    expect(ORDER_STEPS[4].key).toBe("entrega");
  });
});
