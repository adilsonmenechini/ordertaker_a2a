import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { Tabs } from "@/components/Tabs";

const sampleTabs = [
  { id: "tab1", label: "First", content: <div>Content 1</div> },
  { id: "tab2", label: "Second", content: <div>Content 2</div> },
];

describe("Tabs", () => {
  it("renders tab labels", () => {
    render(<Tabs tabs={sampleTabs} />);
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("shows first tab content by default", () => {
    render(<Tabs tabs={sampleTabs} />);
    expect(screen.getByText("Content 1")).toBeInTheDocument();
    expect(screen.queryByText("Content 2")).not.toBeInTheDocument();
  });

  it("switches to second tab on click", () => {
    render(<Tabs tabs={sampleTabs} />);
    fireEvent.click(screen.getByText("Second"));
    expect(screen.getByText("Content 2")).toBeInTheDocument();
    expect(screen.queryByText("Content 1")).not.toBeInTheDocument();
  });

  it("respects activeTab prop", () => {
    render(<Tabs tabs={sampleTabs} activeTab="tab2" />);
    expect(screen.getByText("Content 2")).toBeInTheDocument();
    expect(screen.queryByText("Content 1")).not.toBeInTheDocument();
  });
});
