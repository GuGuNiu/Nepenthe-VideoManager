const { contextBridge, ipcRenderer } = require("electron");

const originalConsoleLog = globalThis.console.log;
const originalConsoleError = globalThis.console.error;

originalConsoleLog('[Preload Script] Initializing...');

ipcRenderer.on("nepenthe-backend-actual-log", (_event, message) => { 
    try {
        window.dispatchEvent(new CustomEvent("on-backend-log-message", { detail: message }));
    } catch (e) {
        originalConsoleError('[Preload Script] Error dispatching "on-backend-log-message" custom event:', e);
    }
});
originalConsoleLog('[Preload Script] IPC listener for "nepenthe-backend-actual-log" registered to dispatch custom events.');

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
    openExternal: (url) => ipcRenderer.send("open-external-link", url),
    getAppVersion: () => ipcRenderer.invoke("get-app-version"),
    checkInitialConfigStatus: () => ipcRenderer.invoke("check-initial-config-status"), 
    onShowInitialSetup: (callback) => { 
        if (typeof callback === 'function') {
            const listener = (_event, needsSetup) => callback(needsSetup);
            ipcRenderer.on("show-initial-setup", listener);
            return () => ipcRenderer.removeListener("show-initial-setup", listener);
        }
        return () => {};
    },
    startBackendManually: () => ipcRenderer.invoke('start-python-backend-manual'), 
    stopBackendManually: () => ipcRenderer.invoke('stop-python-backend-manual'),   
  });
  originalConsoleLog('[Preload Script] electronApp API exposed successfully via contextBridge.');
} catch (error) {
  originalConsoleError("[PreloadScript] Error exposing API to renderer:", error);
}