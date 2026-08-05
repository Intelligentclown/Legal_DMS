/** Mirrors the API surface `electron/preload.ts` exposes via contextBridge. */
export interface ElectronAppInfo {
  name: string;
  version: string;
  environment: string;
}

interface ElectronApi {
  getAppInfo: () => Promise<ElectronAppInfo>;
}

declare global {
  interface Window {
    api?: ElectronApi;
  }
}

export const ipcBridge = {
  isAvailable: (): boolean => typeof window !== "undefined" && Boolean(window.api),

  getAppInfo: (): Promise<ElectronAppInfo> => {
    if (!window.api) {
      throw new Error("Electron IPC bridge is unavailable — not running inside Electron.");
    }
    return window.api.getAppInfo();
  },
};
