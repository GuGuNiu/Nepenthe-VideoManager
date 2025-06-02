import { app, BrowserWindow, ipcMain, shell, Menu, session, dialog } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';
import url from 'node:url';
import Store from 'electron-store';
import { spawn } from 'node:child_process';
import net from 'node:net';

const defaultConfig = {
  apiHost: '127.0.0.1',
  apiPort: 8000,
  internalApiHost: '127.0.0.1',
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

let dataDirRootForApp;
let dataDirRoot;
let dbFilePath;
let thumbnailsStoragePath;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const cliArgs = process.argv.slice(1);
const isServeMode = cliArgs.includes('--serve') && !app.isPackaged;
let viteServePort = 5174;
const portArgIndexCLI = cliArgs.indexOf('--port');
if (portArgIndexCLI !== -1 && cliArgs[portArgIndexCLI + 1]) {
  const parsedPort = parseInt(cliArgs[portArgIndexCLI + 1], 10);
  if (!isNaN(parsedPort)) {
    viteServePort = parsedPort;
  }
}

let mainWindow;
let pythonBackendProcess = null;

// electron/main.js - 确保 initializeEssentialPaths 函数是这样的：

function initializeEssentialPaths() {
  try {
    // electron-store 的配置文件仍然会使用 app.getPath('userData') 下的默认位置或你指定的 cwd
    // 但我们的核心数据 (db, thumbnails) 将根据下面的逻辑确定路径

    if (app.isPackaged) {
      // 打包模式：数据存储在 .exe 所在目录的 "data" 文件夹下
      dataDirRootForApp = path.join(path.dirname(app.getPath('exe')), 'data');
      console.log(`[MainProcess] Packaged mode. App data root (for DB/Thumbnails) set to: ${dataDirRootForApp}`);
    } else {
      // 开发模式：数据存储在项目根目录 (Nepenthe-VideoManager) 的 "data" 文件夹下
      // app.getAppPath() 在开发时是 nepenthe_web_ui 目录 (Electron 项目的根)
      // 我们需要找到 Nepenthe-VideoManager 这个 Python 项目的根目录
      // 假设 nepenthe_web_ui 和 Nepenthe-VideoManager 是同级目录：
      // const mainProjectRootDev = path.resolve(app.getAppPath(), '..', 'Nepenthe-VideoManager');
      // 或者，如果你的 Python 项目就是 nepenthe_web_ui 的上一级：
      const mainProjectRootDev = path.resolve(app.getAppPath(), '..'); 
      dataDirRootForApp = path.join(mainProjectRootDev, 'data');
      console.log(`[MainProcess] Development mode. App data root (for DB/Thumbnails) set to: ${dataDirRootForApp}`);
    }

    if (!fs.existsSync(dataDirRootForApp)) {
        fs.mkdirSync(dataDirRootForApp, { recursive: true });
        console.log(`[MainProcess] Successfully created app data directory: ${dataDirRootForApp}`);
    } else {
        console.log(`[MainProcess] App data directory already exists: ${dataDirRootForApp}`);
    }

    const dbFileNameInternal = 'nepenthe_videos.db';
    dbFilePath = path.join(dataDirRootForApp, dbFileNameInternal); // Python后端将使用这个路径
    const thumbnailsDirNameInternal = 'thumbnails';
    thumbnailsStoragePath = path.join(dataDirRootForApp, thumbnailsDirNameInternal); // Python后端将使用这个路径
    if (!fs.existsSync(thumbnailsStoragePath)) {
        fs.mkdirSync(thumbnailsStoragePath, { recursive: true });
        console.log(`[MainProcess] Successfully created thumbnails directory: ${thumbnailsStoragePath}`);
    } else {
        console.log(`[MainProcess] Thumbnails directory already exists: ${thumbnailsStoragePath}`);
    }
    
    console.log(`[MainProcess] Database file for backend will be at: ${dbFilePath}`);
    console.log(`[MainProcess] Thumbnails for backend will be stored at: ${thumbnailsStoragePath}`);
    return true;
  } catch (error) {
    console.error(`[MainProcess] FATAL ERROR: Could not initialize app data paths. Error: ${error}`);
    dialog.showErrorBox("Data Path Error", `Failed to initialize application data paths.\nError: ${error.message}`);
    app.quit(); // 确保在致命错误时退出
    return false;
  }
}

function getPythonBackendExePath() {
  const backendExecutableName = process.platform === 'win32' ? 'nepenthe_backend.exe' : 'nepenthe_backend';
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'assets', 'backend', backendExecutableName);
  } else {
    return path.resolve(app.getAppPath(), 'dev_backend', 'nepenthe_backend', backendExecutableName);
  }
}

async function findFreePort(startPort = 28000) {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.listen(startPort, '127.0.0.1', () => {
            const port = server.address().port;
            server.close(() => resolve(port));
        });
        server.on('error', (err) => {
            if (err.code === 'EADDRINUSE' || err.code === 'EACCES') {
                resolve(findFreePort(startPort + 1));
            } else {
                reject(err);
            }
        });
    });
}

async function startPythonBackend() {
  if (pythonBackendProcess && pythonBackendProcess.pid && !pythonBackendProcess.killed) {
    if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) mainWindow.webContents.send('backend-log-message', '[INFO][MainProc] Python backend is already running.');
    return store.get('internalApiPort'); 
  }

  const backendExePath = getPythonBackendExePath();
  if (!backendExePath || !fs.existsSync(backendExePath)) {
    const errorMsg = `Python backend executable not found at: ${backendExePath || 'path not determined'}`;
    console.error(`[MainProcess] ${errorMsg}`);
    if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) mainWindow.webContents.send('backend-log-message', `[ERROR][MainProc] ${errorMsg}`);
    return null;
  }

  const apiHostForBackend = '127.0.0.1';
  let actualApiPortForBackend;
  try {
    actualApiPortForBackend = await findFreePort(store.get('internalApiPort', defaultConfig.internalApiPort));
  } catch (portError) {
    console.error('[MainProcess] Could not find a free port for the backend:', portError);
    if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) mainWindow.webContents.send('backend-log-message', `[ERROR][MainProc] Could not find a free port for the backend: ${portError.message}`);
    return null;
  }
  
  store.set('internalApiHost', apiHostForBackend); 
  store.set('internalApiPort', actualApiPortForBackend); 

  const videoPathsFromStore = store.get('videoPaths', []);
  const ffmpegPathFromStore = store.get('ffmpegPath', '');
  const ffprobePathFromStore = store.get('ffprobePath', '');

  const backendArgs = [
    '--host', apiHostForBackend,
    '--port', actualApiPortForBackend.toString(),
    '--video_paths', videoPathsFromStore.join(','),
    '--db-file-path', dbFilePath,
    '--thumbnails-storage-path', thumbnailsStoragePath,
  ];
  if (ffmpegPathFromStore) backendArgs.push('--ffmpeg-path', ffmpegPathFromStore);
  if (ffprobePathFromStore) backendArgs.push('--ffprobe-path', ffprobePathFromStore);

  if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) mainWindow.webContents.send('backend-log-message', `[INFO][MainProc] Starting Python backend (Host: ${apiHostForBackend}, Port: ${actualApiPortForBackend})...`);
  console.log(`[MainProcess] Attempting to start Python backend: ${backendExePath} with args: ${backendArgs.join(' ')}`);
  
  try {
    const backendWorkingDirectory = path.dirname(backendExePath);
    pythonBackendProcess = spawn(backendExePath, backendArgs, { 
        stdio: ['ignore', 'pipe', 'pipe'], // stdin, stdout, stderr
        cwd: backendWorkingDirectory,
        windowsHide: true 
    });

    pythonBackendProcess.stdout.on('data', (data) => {
      const message = data.toString().trim();
      console.log(`[MainProcess FORWARDING STDOUT] ${message}`); // 主进程日志，确认收到
      if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) {
        mainWindow.webContents.send('backend-log-message', `[stdout] ${message}`);
      }
    });
    pythonBackendProcess.stderr.on('data', (data) => {
      const message = data.toString().trim();
      console.error(`[MainProcess FORWARDING STDERR] ${message}`); // 主进程日志，确认收到
      if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) {
        mainWindow.webContents.send('backend-log-message', `[stderr] ${message}`);
      }
    });
    pythonBackendProcess.on('error', (err) => {
      console.error('[MainProcess] Failed to start Python backend process (spawn error):', err);
      if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) mainWindow.webContents.send('backend-log-message', `[ERROR][MainProc] Failed to start Python backend: ${err.message}`);
      pythonBackendProcess = null;
    });
    pythonBackendProcess.on('close', (code) => {
      console.log(`[MainProcess] Python backend process closed with code ${code}`);
      if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) mainWindow.webContents.send('backend-log-message', `[INFO][MainProc] Python backend process exited with code ${code}.`);
      pythonBackendProcess = null;
    });
    console.log(`[MainProcess] Python backend process object created (PID: ${pythonBackendProcess.pid}), should listen on ${apiHostForBackend}:${actualApiPortForBackend}`);
    return actualApiPortForBackend;
  } catch (spawnError) {
    console.error('[MainProcess] Exception while spawning Python backend process:', spawnError);
    if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) mainWindow.webContents.send('backend-log-message', `[ERROR][MainProc] Error spawning Python backend: ${spawnError.message}`);
    pythonBackendProcess = null;
    return null;
  }
}

async function createWindow() {
  const preloadScriptPath = path.join(__dirname, 'preload.js');
  if (!fs.existsSync(preloadScriptPath)) {
    console.error('[MainProcess] FATAL ERROR: Preload script not found at:', preloadScriptPath);
    app.quit(); return;
  }

  mainWindow = new BrowserWindow({
    width: store.get('windowWidth'), height: store.get('windowHeight'),
    minWidth: 1000, minHeight: 600,
    x: store.get('windowX'), y: store.get('windowY'),
    webPreferences: { preload: preloadScriptPath, contextIsolation: true, nodeIntegration: false, devTools: isServeMode },
    icon: path.join(__dirname, '../public/fac.ico')
  });

  mainWindow.on('resized', () => { if(mainWindow && !mainWindow.isMinimized() && !mainWindow.isMaximized()){ const [width, height] = mainWindow.getSize(); store.set('windowWidth', width); store.set('windowHeight', height);}});
  mainWindow.on('moved', () => { if(mainWindow && !mainWindow.isMinimized() && !mainWindow.isMaximized()){ const [x, y] = mainWindow.getPosition(); store.set('windowX', x); store.set('windowY', y);}});
  const winX = store.get('windowX'); const winY = store.get('windowY');
  if (typeof winX === 'number' && typeof winY === 'number') mainWindow.setPosition(winX, winY);
  
  Menu.setApplicationMenu(null);

  let apiHostForFrontend = store.get('internalApiHost');
  let apiPortForFrontend = store.get('internalApiPort');

  const backendPort = await startPythonBackend();
  if (backendPort) {
      apiHostForFrontend = store.get('internalApiHost');
      apiPortForFrontend = store.get('internalApiPort');
  } else {
      console.error("[MainProcess] CRITICAL: Python backend failed to start or returned invalid port.");
      if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) mainWindow.webContents.send('backend-log-message', `[ERROR][MainProc] Python backend failed to start. Please check main process logs.`);
      // Fallback to stored general API settings if internal backend fails
      apiHostForFrontend = store.get('apiHost', defaultConfig.apiHost);
      apiPortForFrontend = store.get('apiPort', defaultConfig.apiPort);
      console.warn(`[MainProcess] Falling back to general API config: http://${apiHostForFrontend}:${apiPortForFrontend}`);
  }
  
  const dynamicApiOrigin = `http://${apiHostForFrontend}:${apiPortForFrontend}`;
  console.log("[MainProcess] API Origin for CSP and Preload:", dynamicApiOrigin);

  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const cspDirectives = [
      `default-src 'self' http://localhost:${viteServePort}`, 
      `script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:${viteServePort}`, 
      `style-src 'self' 'unsafe-inline'`, 
      `img-src 'self' data: http://localhost:${viteServePort} ${dynamicApiOrigin}`, 
      `font-src 'self' data: http://localhost:${viteServePort}`, 
      `connect-src 'self' http://localhost:${viteServePort} ${dynamicApiOrigin}`, 
      `media-src 'self' http://localhost:${viteServePort} ${dynamicApiOrigin}`,
      `object-src 'none'`, `frame-src 'none'`  
    ];
    const cspString = cspDirectives.map(d => d.trim().endsWith(';') ? d.trim() : d.trim() + ';').join(' ');
    callback({ responseHeaders: { ...details.responseHeaders, 'Content-Security-Policy': [cspString] } });
  });

  if (isServeMode) {
    const devUrl = `http://localhost:${viteServePort}`;
    mainWindow.loadURL(devUrl)
      .then(() => { if (mainWindow && !mainWindow.isDestroyed()) { mainWindow.focus(); if (!mainWindow.webContents.isDevToolsOpened()) mainWindow.webContents.openDevTools(); }})
      .catch(err => console.error(`[MainProcess] Failed to load dev URL ${devUrl}:`, err));
  } else { 
    const indexHtmlPath = path.join(__dirname, '../dist/index.html');
    const indexPath = url.format({ pathname: indexHtmlPath, protocol: 'file:', slashes: true, });
    if (!fs.existsSync(indexHtmlPath) && app.isPackaged) {
      console.error('[MainProcess] ERROR: dist/index.html not found:', indexHtmlPath);
    }
    mainWindow.loadURL(indexPath)
      .then(() => { if (mainWindow && !mainWindow.isDestroyed()) mainWindow.focus(); })
      .catch(err => console.error(`[MainProcess] Failed to load production file ${indexPath}:`, err));
  }
  mainWindow.webContents.on('devtools-closed', () => { if (mainWindow && !mainWindow.isDestroyed()) { mainWindow.focus(); setTimeout(() => { if (mainWindow && !mainWindow.isDestroyed()) mainWindow.focus(); }, 100);}});
  mainWindow.on('closed', () => { mainWindow = null; });
}

ipcMain.handle('get-all-configs', () => {
  return {
    apiHost: store.get('internalApiHost'), 
    apiPort: store.get('internalApiPort'),
    videoPaths: store.get('videoPaths'),
    ffmpegPath: store.get('ffmpegPath'), 
    ffprobePath: store.get('ffprobePath'),
    isPackaged: app.isPackaged, 
    dataDir: dataDirRoot 
  };
});
ipcMain.handle('get-config', (event, key) => store.get(key));
ipcMain.handle('set-config', (event, key, value) => { try { store.set(key, value); return { success: true }; } catch (error) { console.error(`[MainProcess] Failed to set config: ${key}`, error); return { success: false, error: error.message };}});
ipcMain.handle('get-platform', () => process.platform);
ipcMain.handle('browse-directory', async () => { const tWin = BrowserWindow.getFocusedWindow()||mainWindow; if(!tWin||tWin.isDestroyed())return null; const r = await dialog.showOpenDialog(tWin,{properties:['openDirectory']}); if(!r.canceled&&r.filePaths.length>0)return r.filePaths[0]; return null;});
ipcMain.handle('browse-file', async (event, options) => { const tWin = BrowserWindow.getFocusedWindow()||mainWindow; if(!tWin||tWin.isDestroyed())return null; const o={properties:['openFile'],title:options?.title||'选择文件',filters:options?.filters||[{name:'所有文件',extensions:['*']}]}; const r=await dialog.showOpenDialog(tWin,o); if(!r.canceled&&r.filePaths.length>0)return r.filePaths[0]; return null;});
ipcMain.on('play-video-locally', (event, videoPath) => { if(videoPath&&typeof videoPath==='string'){shell.openPath(videoPath).catch(err=>console.error(`IPC err: ${err}`));}else{console.error('IPC invalid videoPath');}});
ipcMain.on('show-item-in-folder', (event, itemPath) => { if(itemPath&&typeof itemPath==='string'){shell.showItemInFolder(itemPath);}else{console.error('IPC invalid itemPath');}});
ipcMain.on('open-external-link', (event, extUrl) => { if (extUrl && (extUrl.startsWith('http:') || extUrl.startsWith('https:'))) { shell.openExternal(extUrl); }});
ipcMain.handle('get-app-version', () => app.getVersion());
ipcMain.handle('check-initial-config-status', () => ({ needsSetup: !(store.get('videoPaths', [])).length }));
ipcMain.handle('start-python-backend-manual', async () => { 
    const port = await startPythonBackend();
    return { success: !!port, port: port, host: store.get('internalApiHost') };
});

app.whenReady().then(async () => {
  if (!initializeEssentialPaths()) {
    return; 
  }
  await createWindow(); 
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