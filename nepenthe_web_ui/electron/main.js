import { app, BrowserWindow, ipcMain, shell, Menu } from 'electron'; 
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const args = process.argv.slice(1);
const isServeMode = args.includes('--serve');
let servePort = 5174; // 确保与 package.json 中 vite:serve 端口一致
const portArgIndex = args.indexOf('--port');
if (portArgIndex !== -1 && args[portArgIndex + 1]) {
  const parsedPort = parseInt(args[portArgIndex + 1], 10);
  if (!isNaN(parsedPort)) {
    servePort = parsedPort;
  }
}

let mainWindow;

function createWindow() {
  const preloadScriptPath = path.join(__dirname, 'preload.js');

  if (!fs.existsSync(preloadScriptPath)) {
    console.error('[MainProcess] FATAL ERROR: Preload script NOT FOUND at:', preloadScriptPath);
    // 考虑在这里退出应用或显示错误给用户
    app.quit();
    return;
  }

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: preloadScriptPath,
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  Menu.setApplicationMenu(null);

  if (isServeMode) {
    const devUrl = `http://localhost:${servePort}`;
    console.log(`[MainProcess] Loading dev URL: ${devUrl}`);
    mainWindow.loadURL(devUrl)
      .catch(err => {
        console.error(`[MainProcess] Failed to load dev URL ${devUrl}:`, err);
        console.error(`[MainProcess] Ensure Vite server is running on port ${servePort}.`);
      });
  } else {
    const indexPath = url.format({
      pathname: path.join(__dirname, '../dist/index.html'),
      protocol: 'file:',
      slashes: true,
    });
    console.log(`[MainProcess] Loading production file: ${indexPath}`);
     if (!fs.existsSync(path.join(__dirname, '../dist/index.html'))) {
        console.error('[MainProcess] ERROR: dist/index.html NOT FOUND for production mode.');
        // 在这里可以显示一个错误页面或者退出
    }
    mainWindow.loadURL(indexPath)
      .catch(err => console.error(`[MainProcess] Failed to load production file ${indexPath}:`, err));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow).catch(err => {
  console.error('[MainProcess] Error during app.whenReady:', err);
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

ipcMain.on('play-video-locally', (event, videoPath) => {
  if (videoPath && typeof videoPath === 'string') {
    console.log(`[MainProcess] IPC: Received request to play: ${videoPath}`);
    shell.openPath(videoPath)
      .then(() => console.log(`[MainProcess] IPC: Successfully attempted to open: ${videoPath}`))
      .catch(err => {
        console.error(`[MainProcess] IPC: Failed to open path "${videoPath}" with shell:`, err);
      });
  } else {
    console.error('[MainProcess] IPC: Invalid videoPath received:', videoPath);
  }
});