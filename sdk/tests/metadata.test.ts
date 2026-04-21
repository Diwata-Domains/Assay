import { describe, it, expect, beforeEach } from "vitest";
import { collectMetadata } from "../src/metadata.js";

describe("collectMetadata", () => {
  it("returns an object with required fields", () => {
    const m = collectMetadata();
    expect(m).toHaveProperty("url");
    expect(m).toHaveProperty("viewport");
    expect(m).toHaveProperty("userAgent");
    expect(m).toHaveProperty("capturedAt");
  });

  it("viewport has width and height as numbers", () => {
    const { viewport } = collectMetadata();
    expect(typeof viewport.width).toBe("number");
    expect(typeof viewport.height).toBe("number");
  });

  it("capturedAt is a valid ISO 8601 string", () => {
    const { capturedAt } = collectMetadata();
    expect(() => new Date(capturedAt)).not.toThrow();
    expect(new Date(capturedAt).toISOString()).toBe(capturedAt);
  });

  it("url is a non-empty string", () => {
    const { url } = collectMetadata();
    expect(typeof url).toBe("string");
    expect(url.length).toBeGreaterThan(0);
  });

  it("userAgent is a non-empty string", () => {
    const { userAgent } = collectMetadata();
    expect(typeof userAgent).toBe("string");
    expect(userAgent.length).toBeGreaterThan(0);
  });
});
