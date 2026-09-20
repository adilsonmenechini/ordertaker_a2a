"use client";

import React, { useState, ReactNode } from "react";

interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  activeTab?: string;
}

export function Tabs({ tabs, activeTab: initialTab }: TabsProps) {
  const [activeTab, setActiveTab] = useState(initialTab || tabs[0]?.id);

  return (
    <div className="h-full flex flex-col">
      {/* Tab nav */}
      <nav className="px-5 pt-5 pb-0">
        <div className="flex gap-1 bg-[var(--pv-cream)] rounded-lg p-1">
          {tabs.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`
                flex-1 py-2.5 text-sm font-medium rounded-md transition-all duration-200
                ${
                  activeTab === id
                    ? "bg-white text-[var(--pv-brown)] shadow-sm"
                    : "text-[var(--pv-brown-light)] hover:text-[var(--pv-brown)]"
                }
              `}
            >
              {label}
            </button>
          ))}
        </div>
      </nav>

      {/* Tab content */}
      <main className="p-5 overflow-y-auto flex-1 min-h-0">
        {tabs.find((tab) => tab.id === activeTab)?.content}
      </main>
    </div>
  );
}
