/**
 * Named IPC channels shared between the main process and the preload
 * bridge. Keeping this list explicit (rather than letting the renderer
 * invoke arbitrary channel strings) is what makes the contextBridge
 * surface in `preload.ts` safe to expose.
 */
export const IpcChannels = {
  APP_INFO: "app:get-info",
} as const;

export type IpcChannel = (typeof IpcChannels)[keyof typeof IpcChannels];
