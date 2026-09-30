/**
 * Saves an already-fetched blob under `filename` using a temporary object URL.
 *
 * The bytes arrive from the backend's download route, which has already
 * verified their integrity; nothing here re-derives or inspects the content.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  URL.revokeObjectURL(url);
}
