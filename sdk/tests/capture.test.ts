import { describe, it, expect, vi, beforeEach } from "vitest";
import { AssaySDK } from "../src/index.js";

vi.mock("html2canvas", () => ({
  default: vi.fn(async () => ({ toDataURL: () => "data:image/png;base64,abc123" })),
}));

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

const sdk = new AssaySDK({ apiKey: "test-key", endpoint: "http://localhost:8000" });

beforeEach(() => {
  mockFetch.mockReset();
});

describe("AssaySDK.capture()", () => {
  it("POSTs to /ingest on the configured endpoint", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: "accepted" }) });
    await sdk.capture();
    expect(mockFetch).toHaveBeenCalledOnce();
    const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/ingest");
  });

  it("sends X-Assay-Key header", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: "accepted" }) });
    await sdk.capture();
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["X-Assay-Key"]).toBe("test-key");
  });

  it("sends Content-Type application/json", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: "accepted" }) });
    await sdk.capture();
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("includes screenshot in payload", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: "accepted" }) });
    await sdk.capture();
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    expect(body.screenshot).toBe("abc123");
  });

  it("includes metadata fields in payload", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: "accepted" }) });
    await sdk.capture();
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    expect(body.url).toBeDefined();
    expect(body.viewport).toBeDefined();
    expect(body.user_agent).toBeDefined();
    expect(body.captured_at).toBeDefined();
  });

  it("passes user_comment when provided", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: "accepted" }) });
    await sdk.capture({ comment: "looks broken" });
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    expect(body.user_comment).toBe("looks broken");
  });

  it("sends null user_comment when omitted", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: "accepted" }) });
    await sdk.capture();
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    expect(body.user_comment).toBeNull();
  });

  it("returns the server response body", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: "accepted" }) });
    const result = await sdk.capture();
    expect(result).toEqual({ status: "accepted" });
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 401 });
    await expect(sdk.capture()).rejects.toThrow("status 401");
  });

  it("normalises trailing slash on endpoint", async () => {
    const sdk2 = new AssaySDK({ apiKey: "k", endpoint: "http://localhost:8000/" });
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: "accepted" }) });
    await sdk2.capture();
    const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/ingest");
  });
});
