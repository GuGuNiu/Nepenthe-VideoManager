const { contextBridge, ipcRenderer } = require('electron');

//console.log('[预加载脚本] 尝试执行 (CJS 版本)。');

try {
  contextBridge.exposeInMainWorld('electronAPI', {
    playVideoLocally: (filePath) => {
      //console.log('[预加载脚本] IPC: 发送 play-video-locally 消息，路径 (CJS):', filePath);
      ipcRenderer.send('play-video-locally', filePath);
    },

    showItemInFolder: (itemPath) => ipcRenderer.send('show-item-in-folder', itemPath) 
  });
  //console.log('[预加载脚本] electronAPI 已成功暴露 (CJS 版本)。');
} catch (error) {
  console.error('[预加载脚本] 暴露 electronAPI 时发生错误 (CJS 版本):', error);
}