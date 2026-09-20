"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { OrderStateProvider } from "@/components/OrderState";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit" showDevConsole={false}>
      <OrderStateProvider>{children}</OrderStateProvider>
    </CopilotKit>
  );
}
