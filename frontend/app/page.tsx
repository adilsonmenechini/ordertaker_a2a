"use client";

import dynamic from "next/dynamic";
import { Tabs } from "@/components/Tabs";
import { OrderDetails } from "@/components/OrderDetails";
import { StateVisualizer } from "@/components/StateVisualizer";
import { useOrderState } from "@/components/OrderState";

const Chat = dynamic(() => import("@/components/Chat").then((m) => m.Chat), {
  ssr: false,
});

export default function Page() {
  const { order, currentStep } = useOrderState();

  const tabs = [
    {
      id: "pedido",
      label: "Pedido",
      content: <OrderDetails order={order} />,
    },
    {
      id: "andamento",
      label: "Andamento",
      content: <StateVisualizer currentStep={currentStep} />,
    },
  ];

  return (
    <div className="h-screen w-screen grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-3 p-3 lg:p-5">
      {/* Left: Tabs */}
      <div className="overflow-y-auto rounded-xl border border-[#f0e6da] bg-white min-h-0">
        <Tabs tabs={tabs} activeTab="pedido" />
      </div>

      {/* Right: Chat */}
      <div className="flex justify-center items-center overflow-y-auto rounded-xl min-h-0">
        <Chat className="w-full h-full" />
      </div>
    </div>
  );
}
