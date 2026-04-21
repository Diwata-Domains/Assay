import html2canvas from "html2canvas";

export async function captureScreenshot(): Promise<string> {
  const canvas = await html2canvas(document.body);
  return canvas.toDataURL("image/png").replace(/^data:image\/png;base64,/, "");
}
