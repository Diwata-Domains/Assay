import { describe, it, expect } from "vitest";
import { AssaySDK } from "../src/index.js";

describe("AssaySDK", () => {
  it("is importable", () => {
    expect(AssaySDK).toBeDefined();
  });

  it("constructs with valid config", () => {
    const sdk = new AssaySDK({ apiKey: "test-key-abc", endpoint: "http://localhost:8000" });
    expect(sdk).toBeInstanceOf(AssaySDK);
  });

  it("stores apiKey", () => {
    const sdk = new AssaySDK({ apiKey: "my-key", endpoint: "http://localhost:8000" });
    expect(sdk.apiKey).toBe("my-key");
  });

  it("stores endpoint", () => {
    const sdk = new AssaySDK({ apiKey: "my-key", endpoint: "http://localhost:8000" });
    expect(sdk.endpoint).toBe("http://localhost:8000");
  });

  it("throws on empty apiKey", () => {
    expect(() => new AssaySDK({ apiKey: "", endpoint: "http://localhost:8000" })).toThrow(
      "apiKey must be a non-empty string"
    );
  });

  it("throws on whitespace-only apiKey", () => {
    expect(() => new AssaySDK({ apiKey: "   ", endpoint: "http://localhost:8000" })).toThrow(
      "apiKey must be a non-empty string"
    );
  });

  it("throws on empty endpoint", () => {
    expect(() => new AssaySDK({ apiKey: "my-key", endpoint: "" })).toThrow(
      "endpoint must be a non-empty string"
    );
  });

  it("throws on whitespace-only endpoint", () => {
    expect(() => new AssaySDK({ apiKey: "my-key", endpoint: "   " })).toThrow(
      "endpoint must be a non-empty string"
    );
  });
});
