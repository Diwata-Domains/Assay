export interface CaptureMetadata {
  url: string;
  viewport: { width: number; height: number };
  userAgent: string;
  capturedAt: string;
}

export function collectMetadata(): CaptureMetadata {
  return {
    url: window.location.href,
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
    },
    userAgent: navigator.userAgent,
    capturedAt: new Date().toISOString(),
  };
}
