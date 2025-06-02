const { contextBridge, ipcRenderer } = require("electron");

try {
  contextBridge.exposeInMainWorld("electronApp", {
    getAppConfig: async () => ipcRenderer.invoke("get-all-configs"),
    getConfigKey: (key) => ipcRenderer.invoke("get-config", key),
    setConfigKey: (key, value) => ipcRenderer.invoke("set-config", key, value),
    getPlatform: () => ipcRenderer.invoke("get-platform"),
    browseDirectory: () => ipcRenderer.invoke("browse-directory"),
    browseFile: (options) => ipcRenderer.invoke("browse-file", options),
    playVideoLocally: (videoPath) => ipcRenderer.send("play-video-locally", videoPath),
    showItemInFolder: (itemPath) => ipcRenderer.send("show-item-in-folder", itemPath),
    onBackendLogMessage: (callback) => {
      const listener = (_event, message) => callback(message);
      ipcRenderer.on("backend-log-message", listener);
      return () => ipcRenderer.removeListener("backend-log-message", listener);
    },
    openExternal: (url) => ipcRenderer.send("open-external-link", url),
    getAppVersion: () => ipcRenderer.invoke("get-app-version"),
    checkInitialConfigStatus: () => ipcRenderer.invoke("check-initial-config-status"), 
    onShowInitialSetup: (callback) => ipcRenderer.on("show-initial-setup", (_event, needsSetup) => callback(needsSetup)),
  });
} catch (error) {
  console.error("[PreloadScript] Error exposing API to renderer:", error);
}
