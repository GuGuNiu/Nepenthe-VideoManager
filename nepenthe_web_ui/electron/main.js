import { app, BrowserWindow, ipcMain, shell, Menu, session, dialog } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';
import url from 'node:url';
import Store from 'electron-store';
import { spawn } from 'node:child_process';

const defaultConfig = {
  apiHost: '127.0.0.1',
  apiPort: 8000,
  internalApiPort: 28000,
  videoPaths: [],
  ffmpegPath: '',
  ffprobePath: '',
  windowWidth: 1600,
  windowHeight: 900,
  windowX: undefined,
  windowY: undefined,
};
const store = new Store({ defaults: defaultConfig });

const appUserDataPath = app.getPath('userData');
const dataDirRoot = path.join(appUserDataPath, 'NepentheVideoManagerData');
if (!fs.existsSync(dataDirRoot)) {
  fs.mkdirSync(dataDirRoot, { recursive: true });
}
const dbFileName = 'nepenthe_videos.db';
const dbFilePath = path.join(dataDirRoot, dbFileName);
const thumbnailsDirName = 'thumbnails';
const thumbnailsStoragePath = path.join(dataDirRoot, thumbnailsDirName);
if (!fs.existsSync(thumbnailsStoragePath)) {
  fs.mkdirSync(thumbnailsStoragePath, { recursive: true });
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const args = process.argv.slice(1);
const isServeMode = args.includes('--serve');
let viteServePort = 5174;
const portArgIndex = args.indexOf('--port');
if (portArgIndex !== -1 && args[portArgIndex + 1]) {
  const parsedPort = parseInt(args[portArgIndex + 1], 10);
  if (!isNaN(parsedPort)) {
    viteServePort = parsedPort;
  }
}
console.log(`[MainProcess] Electron launch arguments: ${args.join(' ')}, isDevMode (Vite): ${isServeMode}, viteServePort: ${viteServePort}, isPackaged: ${app.isPackaged}`);

let mainWindow;
let pythonBackendProcess = null;

function getPythonBackendExePath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend', 'nepenthe_backend.exe');
  } else {
    const devBackendPath = path.resolve(__dirname, '../../../Nepenthe-VideoManager/dist/nepenthe_backend_dist/nepenthe_backend.exe');
    if (!fs.existsSync(devBackendPath)) {
      console.warn(`[MainProcess] Development backend executable not found at: ${devBackendPath}. Please ensure Python backend is packaged.`);
      return null;
    }
    return devBackendPath;
  }
}

async function startPythonBackend() {
  if (pythonBackendProcess && pythonBackendProcess.pid && !pythonBackendProcess.killed) {
    console.log('[MainProcess] Python backend is already running.');
    if (mainWindow && mainWindow.webContents) mainWindow.webContents.send('backend-log-message', '[INFO] Python backend is already running.');
    return;
  }

  const backendExePath = getPythonBackendExePath();
  if (!backendExePath || !fs.existsSync(backendExePath)) {
    const errorMsg = `[MainProcess] Python backend executable not found at: ${backendExePath || 'path not determined'}`;
    console.error(errorMsg);
    if (mainWindow && mainWindow.webContents) mainWindow.webContents.send('backend-log-message', `[ERROR] ${errorMsg}`);
    return;
  }

  const apiHostForBackend = '127.0.0.1';
  const apiPortForBackend = store.get('internalApiPort');
  const videoPathsFromStore = store.get('videoPaths', []);
  const ffmpegPathFromStore = store.get('ffmpegPath', '');
  const ffprobePathFromStore = store.get('ffprobePath', '');

  const backendArgs = [
    '--host', apiHostForBackend,
    '--port', apiPortForBackend.toString(),
    '--video_paths', videoPathsFromStore.join(','),
    '--db-file-path', dbFilePath,
    '--thumbnails-storage-path', thumbnailsStoragePath,
  ];
  if (ffmpegPathFromStore) backendArgs.push('--ffmpeg-path', ffmpegPathFromStore);
  if (ffprobePathFromStore) backendArgs.push('--ffprobe-path', ffprobePathFromStore);

  const commandString = `"${backendExePath}" ${backendArgs.join(' ')}`;
  console.log(`[MainProcess] Starting Python backend: ${commandString}`);
  if (mainWindow && mainWindow.webContents) mainWindow.webContents.send('backend-log-message', `[INFO] Starting Python backend at ${apiHostForBackend}:${apiPortForBackend}...`);

  try {
    pythonBackendProcess = spawn(backendExePath, backendArgs, { stdio: ['ignore', 'pipe', 'pipe'] });

    pythonBackendProcess.stdout.on('data', (data) => {
      const message = data.toString().trim();
      console.log(`[PythonBackend STDOUT] ${message}`);
      if (mainWindow && mainWindow.webContents) mainWindow.webContents.send('backend-log-message', `[stdout] ${message}`);
    });
    pythonBackendProcess.stderr.on('data', (data) => {
      const message = data.toString().trim();
      console.error(`[PythonBackend STDERR] ${message}`);
      if (mainWindow && mainWindow.webContents) mainWindow.webContents.send('backend-log-message', `[stderr] ${message}`);
    });
    pythonBackendProcess.on('error', (err) => {
      console.error('[MainProcess] Failed to start Python backend process:', err);
      if (mainWindow && mainWindow.webContents) mainWindow.webContents.send('backend-log-message', `[ERROR] Failed to start Python backend: ${err.message}`);
      pythonBackendProcess = null;
    });
    pythonBackendProcess.on('close', (code) => {
      console.log(`[MainProcess] Python backend process closed with code ${code}`);
      if (mainWindow && mainWindow.webContents) mainWindow.webContents.send('backend-log-message', `[INFO] Python backend process exited with code ${code}.`);
      pythonBackendProcess = null;
    });
  } catch (spawnError) {
    console.error('[MainProcess] Error spawning Python backend process:', spawnError);
    if (mainWindow && mainWindow.webContents) mainWindow.webContents.send('backend-log-message', `[ERROR] Error spawning Python backend: ${spawnError.message}`);
    pythonBackendProcess = null;
  }
}

function createWindow() {
  const preloadScriptPath = path.join(__dirname, 'preload.js');
  if (!fs.existsSync(preloadScriptPath)) {
    console.error('[MainProcess] FATAL ERROR: Preload script not found at:', preloadScriptPath);
    app.quit();
    return;
  }

  mainWindow = new BrowserWindow({
    width: store.get('windowWidth'),
    height: store.get('windowHeight'),
    minWidth: 1000,
    minHeight: 600,
    x: store.get('windowX'),
    y: store.get('windowY'),
    webPreferences: {
      preload: preloadScriptPath,
      contextIsolation: true,
      nodeIntegration: false,
      devTools: isServeMode
    },
    icon: path.join(__dirname, '../public/fac.ico')
  });

  mainWindow.on('resized', () => {
    if (mainWindow && !mainWindow.isMinimized() && !mainWindow.isMaximized()) {
      const [width, height] = mainWindow.getSize();
      store.set('windowWidth', width);
      store.set('windowHeight', height);
    }
  });
  mainWindow.on('moved', () => {
    if (mainWindow && !mainWindow.isMinimized() && !mainWindow.isMaximized()) {
      const [x, y] = mainWindow.getPosition();
      store.set('windowX', x);
      store.set('windowY', y);
    }
  });

  const winX = store.get('windowX');
  const winY = store.get('windowY');
  if (typeof winX === 'number' && typeof winY === 'number') {

    mainWindow.setPosition(winX, winY);
  }
  Menu.setApplicationMenu(null);

  let apiOriginForCSP;
  if (app.isPackaged) {
    startPythonBackend();
    const internalApiHost = '127.0.0.1';
    const internalApiPort = store.get('internalApiPort');
    apiOriginForCSP = `http://${internalApiHost}:${internalApiPort}`;
  } else {
    const devApiHost = store.get('apiHost');
    const devApiPort = store.get('apiPort');
    apiOriginForCSP = `http://${devApiHost}:${devApiPort}`;
  }
  console.log("[MainProcess] API Origin for CSP:", apiOriginForCSP);

  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const cspDirectives = [
      `default-src 'self' http://localhost:${viteServePort}`,
      `script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:${viteServePort}`,
      `style-src 'self' 'unsafe-inline'`,
      `img-src 'self' data: http://localhost:${viteServePort} ${apiOriginForCSP}`,
      `font-src 'self' data: http://localhost:${viteServePort}`,
      `connect-src 'self' http://localhost:${viteServePort} ${apiOriginForCSP}`,
      `media-src 'self' http://localhost:${viteServePort} ${apiOriginForCSP}`,
      `object-src 'none'`,
      `frame-src 'none'`
    ];
    const cspString = cspDirectives.map(d => d.trim().endsWith(';') ? d.trim() : d.trim() + ';').join(' ');
    callback({ responseHeaders: { ...details.responseHeaders, 'Content-Security-Policy': [cspString] } });
  });

  if (isServeMode && !app.isPackaged) { // 开发模式，加载 Vite URL
    const devUrl = `http://localhost:${viteServePort}`;
    mainWindow.loadURL(devUrl)
      .then(() => { if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.openDevTools(); })
      .catch(err => console.error(`[MainProcess] Failed to load dev URL ${devUrl}:`, err));
  } else { // 打包模式或非Vite服务模式，加载本地文件
    const indexHtmlPath = path.join(__dirname, '../dist/index.html');
    const indexPath = url.format({ pathname: indexHtmlPath, protocol: 'file:', slashes: true, });
    if (!fs.existsSync(indexHtmlPath) && app.isPackaged) { // 仅在打包后检查，开发时可能还未构建
      console.error('[MainProcess] ERROR: dist/index.html not found:', indexHtmlPath);
    }
    mainWindow.loadURL(indexPath)
      .catch(err => console.error(`[MainProcess] Failed to load production file ${indexPath}:`, err));
  }
  mainWindow.on('closed', () => { mainWindow = null; });
}

ipcMain.handle('get-all-configs', () => {
  let apiHostToReturn = store.get('apiHost');
  let apiPortToReturn = store.get('apiPort');
  if (app.isPackaged) {
    apiHostToReturn = '127.0.0.1';
    apiPortToReturn = store.get('internalApiPort');
  }
  return {
    apiHost: apiHostToReturn,
    apiPort: apiPortToReturn,
    videoPaths: store.get('videoPaths'),
    ffmpegPath: store.get('ffmpegPath'),
    ffprobePath: store.get('ffprobePath'),
    isPackaged: app.isPackaged,
    dataDir: dataDirRoot
  };
});
ipcMain.handle('get-config', (event, key) => store.get(key));
ipcMain.handle('set-config', (event, key, value) => {
  try { store.set(key, value); return { success: true }; }
  catch (error) { console.error(`[MainProcess] Failed to set config: ${key}`, error); return { success: false, error: error.message }; }
});

ipcMain.handle('get-platform', () => process.platform);

ipcMain.handle('browse-directory', async () => {
  const targetWindow = BrowserWindow.getFocusedWindow() || mainWindow;
  if (!targetWindow || targetWindow.isDestroyed()) return null;
  const result = await dialog.showOpenDialog(targetWindow, { properties: ['openDirectory'] });
  if (!result.canceled && result.filePaths.length > 0) return result.filePaths[0];
  return null;
});
ipcMain.handle('browse-file', async (event, options) => {
  const targetWindow = BrowserWindow.getFocusedWindow() || mainWindow;
  if (!targetWindow || targetWindow.isDestroyed()) return null;
  const dialogOptions = { properties: ['openFile'], title: options?.title || '选择文件', filters: options?.filters || [{ name: '所有文件', extensions: ['*'] }] };
  const result = await dialog.showOpenDialog(targetWindow, dialogOptions);
  if (!result.canceled && result.filePaths.length > 0) return result.filePaths[0];
  return null;
});

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
}).catch(err => console.error('[MainProcess] Error during app.whenReady:', err));

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });

app.on('will-quit', () => {
  if (pythonBackendProcess && !pythonBackendProcess.killed) {
    console.log('[MainProcess] Attempting to terminate Python backend process before quit...');
    const killed = pythonBackendProcess.kill('SIGTERM');
    console.log(`[MainProcess] Python backend process kill signal sent, success: ${killed}`);
    pythonBackendProcess = null;
  }
});

ipcMain.on('play-video-locally', (event, videoPath) => {
  if (videoPath && typeof videoPath === 'string') {
    shell.openPath(videoPath).catch(err => console.error(`[MainProcess] IPC: Failed to open path "${videoPath}":`, err));
  } else { console.error('[MainProcess] IPC: Received invalid videoPath for play-video-locally:', videoPath); }
});
ipcMain.on('show-item-in-folder', (event, itemPath) => {
  if (itemPath && typeof itemPath === 'string') { shell.showItemInFolder(itemPath); }
  else { console.error('[MainProcess] IPC: Received invalid itemPath for show-item-in-folder:', itemPath); }
});


ipcMain.on('open-external-link', (event, url) => {
  if (url && (url.startsWith('http:') || url.startsWith('https:'))) {
    shell.openExternal(url);
  } else {
    console.warn('[MainProcess] Attempted to open invalid external URL:', url);
  }
});

ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});