import { describe, it, expect, vi, beforeEach } from "vitest";
import { captureScreenshot } from "../src/screenshot.js";

vi.mock("html2canvas", () => ({
  default: vi.fn(async () => ({
    toDataURL: () => "data:image/png;base64,abc123",
  })),
}));

describe("captureScreenshot", () => {
  it("returns a base64 string", async () => {
    const result = await captureScreenshot();
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });

  it("strips the data URI prefix", async () => {
    const result = await captureScreenshot();
    expect(result).not.toContain("data:image/png;base64,");
  });

  it("returns the raw base64 payload", async () => {
    const result = await captureScreenshot();
    expect(result).toBe("abc123");
  });

  it("calls html2canvas with document.body", async () => {
    const html2canvas = (await import("html2canvas")).default;
    await captureScreenshot();
    expect(html2canvas).toHaveBeenCalledWith(document.body);
  });
});
