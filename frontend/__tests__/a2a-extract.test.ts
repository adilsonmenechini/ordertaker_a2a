import { describe, it, expect } from "vitest";
import { extractAllReplyText } from "@/app/api/copilotkit/[...slug]/route";

describe("extractAllReplyText", () => {
  it("concatenates all message parts from message.parts (A2A response)", () => {
    // Actual A2A JSON-RPC response structure: body.result has .message
    const response = {
      message: {
        role: "ROLE_AGENT",
        parts: [
          { text: "🔥 Aquecendo o óleo..." },
          { text: "🥟 Massa sendo aberta..." },
          { text: "🍟 Fritando... golden & crispy!" },
        ],
      },
    };

    const result = extractAllReplyText(response);
    expect(result).toContain("Aquecendo");
    expect(result).toContain("Massa");
    expect(result).toContain("Fritando");
    expect(result).toContain("\n");
  });

  it("concatenates all message parts from status.message.parts (long-running task)", () => {
    const response = {
      task: {
        status: {
          message: {
            role: "ROLE_AGENT",
            parts: [
              { text: "📦 Emfatando a embalagem..." },
              { text: "✅ Pronto para entrega!" },
            ],
          },
        },
      },
    };

    const result = extractAllReplyText(response);
    expect(result).toContain("Emfatando");
    expect(result).toContain("Pronto");
  });

  it("concatenates artifact parts", () => {
    const response = {
      task: {
        artifacts: [
          {
            parts: [
              { text: "Step 1" },
              { text: "Step 2" },
            ],
          },
        ],
      },
    };

    const result = extractAllReplyText(response);
    expect(result).toContain("Step 1");
    expect(result).toContain("Step 2");
  });

  it("returns empty string for empty response", () => {
    const response = {};
    const result = extractAllReplyText(response);
    expect(result).toBe("");
  });

  it("handles parts without text gracefully", () => {
    const response = {
      message: {
        role: "ROLE_AGENT",
        parts: [
          { text: "Valid" },
          { not_text: "ignored" },
          { text: "Also valid" },
        ],
      },
    };

    const result = extractAllReplyText(response);
    expect(result).toContain("Valid");
    expect(result).toContain("Also valid");
  });
});