import { contextBridge, ipcRenderer } from "electron";

import { IpcChannels } from "./ipc/channels";

/**
 * The only surface the renderer ever gets: a small set of explicitly
 * named, typed functions — never a generic `invoke(channel, ...)` passthrough,
 * which would let renderer code call arbitrary IPC channels.
 */
const api = {
  getAppInfo: (): Promise<{ name: string; version: string; environment: string }> =>
    ipcRenderer.invoke(IpcChannels.APP_INFO),
  setRefreshToken: (token: string): Promise<void> =>
    ipcRenderer.invoke(IpcChannels.AUTH_STORE_REFRESH_TOKEN, token),
  getRefreshToken: (): Promise<string | null> =>
    ipcRenderer.invoke(IpcChannels.AUTH_GET_REFRESH_TOKEN),
  clearRefreshToken: (): Promise<void> =>
    ipcRenderer.invoke(IpcChannels.AUTH_CLEAR_REFRESH_TOKEN),
} as const;

contextBridge.exposeInMainWorld("api", api);

export type ElectronApi = typeof api;
