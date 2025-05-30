const { contextBridge, ipcRenderer } = require('electron');

try {
  contextBridge.exposeInMainWorld('electronAPI', {
    playVideoLocally: (filePath) => {
      console.log('[Preload] IPC: Sending play-video-locally with path:', filePath);
      ipcRenderer.send('play-video-locally', filePath);
    }
  });
} catch (error) {
  console.error('[Preload] Error exposing electronAPI:', error);
}