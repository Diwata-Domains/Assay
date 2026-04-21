import { captureScreenshot } from "./screenshot.js";
import { collectMetadata } from "./metadata.js";

export interface AssaySDKConfig {
  apiKey: string;
  endpoint: string;
}

export interface CaptureOptions {
  comment?: string;
}

export interface CaptureResult {
  status: string;
}

export class AssaySDK {
  readonly apiKey: string;
  readonly endpoint: string;

  constructor(config: AssaySDKConfig) {
    if (!config.apiKey || config.apiKey.trim() === "") {
      throw new Error("AssaySDK: apiKey must be a non-empty string");
    }
    if (!config.endpoint || config.endpoint.trim() === "") {
      throw new Error("AssaySDK: endpoint must be a non-empty string");
    }
    this.apiKey = config.apiKey;
    this.endpoint = config.endpoint;
  }

  async capture(options: CaptureOptions = {}): Promise<CaptureResult> {
    const [screenshot, meta] = await Promise.all([captureScreenshot(), collectMetadata()]);

    const payload = {
      captured_at: meta.capturedAt,
      url: meta.url,
      viewport: meta.viewport,
      user_agent: meta.userAgent,
      screenshot,
      user_comment: options.comment ?? null,
      metadata: {},
    };

    const ingestUrl = this.endpoint.replace(/\/$/, "") + "/ingest";
    const response = await fetch(ingestUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Assay-Key": this.apiKey,
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`AssaySDK: ingest request failed with status ${response.status}`);
    }

    return response.json() as Promise<CaptureResult>;
  }
}
