/**
 * Named IPC channels shared between the main process and the preload
 * bridge. Keeping this list explicit (rather than letting the renderer
 * invoke arbitrary channel strings) is what makes the contextBridge
 * surface in `preload.ts` safe to expose.
 */
export const IpcChannels = {
  APP_INFO: "app:get-info",
  AUTH_STORE_REFRESH_TOKEN: "auth:store-refresh-token",
  AUTH_GET_REFRESH_TOKEN: "auth:get-refresh-token",
  AUTH_CLEAR_REFRESH_TOKEN: "auth:clear-refresh-token",
} as const;

export type IpcChannel = (typeof IpcChannels)[keyof typeof IpcChannels];
