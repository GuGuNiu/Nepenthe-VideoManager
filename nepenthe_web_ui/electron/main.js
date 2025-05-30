// electron/main.js
import { app, BrowserWindow, ipcMain, shell, Menu } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';
import url from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const args = process.argv.slice(1);
const isServeMode = args.includes('--serve');
let servePort = 5174;
const portArgIndex = args.indexOf('--port');
if (portArgIndex !== -1 && args[portArgIndex + 1]) {
  const parsedPort = parseInt(args[portArgIndex + 1], 10);
  if (!isNaN(parsedPort)) {
    servePort = parsedPort;
  }
}
// 中文日志示例
console.log(`[主进程] Electron启动参数: ${args.join(' ')}, 是否开发模式: ${isServeMode}, 服务端口: ${servePort}`);

let mainWindow;

function createWindow() {
  console.log('[主进程] createWindow函数开始执行。');
  const preloadScriptPath = path.join(__dirname, 'preload.js');
  console.log('[主进程] Preload脚本预期路径:', preloadScriptPath);

  if (!fs.existsSync(preloadScriptPath)) {
    console.error('[主进程] 致命错误: Preload脚本未找到:', preloadScriptPath);
    app.quit();
    return;
  }
  console.log('[主进程] Preload脚本文件存在。');

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: preloadScriptPath,
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, '../public/fac.ico') 
  });
  console.log('[主进程] BrowserWindow实例已创建。');

  Menu.setApplicationMenu(null);

  if (isServeMode) {
    const devUrl = `http://localhost:${servePort}`;
    console.log(`[主进程] 开发模式，加载URL: ${devUrl}`);
    mainWindow.loadURL(devUrl)
      .then(() => {
        console.log(`[主进程] 成功加载URL: ${devUrl}`);
      })
      .catch(err => {
        console.error(`[主进程] 加载开发URL ${devUrl} 失败:`, err);
        console.error(`[主进程] 请确保Vite开发服务器正在端口 ${servePort} 上运行。`);
      });
    mainWindow.webContents.openDevTools();
    console.log('[主进程] 开发模式下已打开开发者工具。');
  } else {
    const indexHtmlPath = path.join(__dirname, '../dist/index.html');
    const indexPath = url.format({
      pathname: indexHtmlPath,
      protocol: 'file:',
      slashes: true,
    });
    console.log(`[主进程] 生产模式，加载文件: ${indexPath}`);
     if (!fs.existsSync(indexHtmlPath)) {
        console.error('[主进程] 错误: 生产模式下 dist/index.html 未找到于路径:', indexHtmlPath);
    }
    mainWindow.loadURL(indexPath)
      .then(() => console.log(`[主进程] 成功加载文件: ${indexPath}`))
      .catch(err => console.error(`[主进程] 加载生产文件 ${indexPath} 失败:`, err));
  }

  mainWindow.on('closed', () => {
    console.log('[主进程] MainWindow已关闭。');
    mainWindow = null;
  });
}

app.whenReady().then(() => {
    console.log('[主进程] App已就绪，调用createWindow。');
    createWindow();
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
        console.log('[主进程] App已激活且无窗口打开，调用createWindow。');
        createWindow();
        }
    });
}).catch(err => {
  console.error('[主进程] app.whenReady期间发生错误:', err);
});

app.on('window-all-closed', () => {
  console.log('[主进程] 所有窗口已关闭。');
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('quit', () => {
  console.log('[主进程] App退出。');
});

ipcMain.on('play-video-locally', (event, videoPath) => {
  if (videoPath && typeof videoPath === 'string') {
    console.log(`[主进程] IPC 'play-video-locally': 收到播放请求: ${videoPath}`);
    shell.openPath(videoPath)
      .then(() => console.log(`[主进程] IPC 'play-video-locally': 成功尝试打开: ${videoPath}`))
      .catch(err => {
        console.error(`[主进程] IPC 'play-video-locally': 使用shell打开路径 "${videoPath}" 失败:`, err);
      });
  } else {
    console.error('[主进程] IPC \'play-video-locally\': 收到无效的videoPath:', videoPath);
  }
});