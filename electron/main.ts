import fs from "node:fs";
import path from "node:path";
import { app, BrowserWindow, ipcMain, safeStorage, shell } from "electron";

import { IpcChannels } from "./ipc/channels";

const REFRESH_TOKEN_FILE = "refresh-token.enc";

function getRefreshTokenPath(): string {
  return path.join(app.getPath("userData"), REFRESH_TOKEN_FILE);
}

const isDev = !app.isPackaged;
const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL ?? "http://localhost:5173";

function createMainWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 1280,
    height: 800,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      // Security baseline: no Node access in the renderer, isolated
      // context for the preload bridge, and a sandboxed renderer process.
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
    },
  });

  window.once("ready-to-show", () => window.show());

  // Only allow navigating within the app itself; open anything else
  // (external links, etc.) in the OS browser instead of inside Electron.
  window.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url);
    return { action: "deny" };
  });
  window.webContents.on("will-navigate", (event, url) => {
    const isDevServer = isDev && url.startsWith(DEV_SERVER_URL);
    const isPackagedApp = !isDev && url.startsWith("file://");
    if (!isDevServer && !isPackagedApp) {
      event.preventDefault();
      void shell.openExternal(url);
    }
  });

  if (isDev) {
    void window.loadURL(DEV_SERVER_URL);
    window.webContents.openDevTools();
  } else {
    void window.loadFile(path.join(__dirname, "../frontend/dist/index.html"));
  }

  return window;
}

function registerIpcHandlers(): void {
  ipcMain.handle(IpcChannels.APP_INFO, () => ({
    name: app.getName(),
    version: app.getVersion(),
    environment: isDev ? "development" : "production",
  }));

  ipcMain.handle(IpcChannels.AUTH_STORE_REFRESH_TOKEN, (_event, token: string) => {
    if (!safeStorage.isEncryptionAvailable()) {
      return;
    }
    const encrypted = safeStorage.encryptString(token);
    fs.writeFileSync(getRefreshTokenPath(), encrypted);
  });

  ipcMain.handle(IpcChannels.AUTH_GET_REFRESH_TOKEN, () => {
    if (!safeStorage.isEncryptionAvailable()) {
      return null;
    }
    const tokenPath = getRefreshTokenPath();
    if (!fs.existsSync(tokenPath)) {
      return null;
    }
    const encrypted = fs.readFileSync(tokenPath);
    return safeStorage.decryptString(encrypted);
  });

  ipcMain.handle(IpcChannels.AUTH_CLEAR_REFRESH_TOKEN, () => {
    const tokenPath = getRefreshTokenPath();
    if (fs.existsSync(tokenPath)) {
      fs.unlinkSync(tokenPath);
    }
  });
}

app.whenReady().then(() => {
  registerIpcHandlers();
  createMainWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
