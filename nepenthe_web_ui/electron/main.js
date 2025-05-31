import { app, BrowserWindow, ipcMain, shell, Menu, session } from 'electron'; 
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
console.log(`[MainProcess] Electron launch arguments: ${args.join(' ')}, isDevMode: ${isServeMode}, servePort: ${servePort}`);

let mainWindow;

function createWindow() {
  console.log('[MainProcess] createWindow function invoked.');
  const preloadScriptPath = path.join(__dirname, 'preload.js');
  if (!fs.existsSync(preloadScriptPath)) {
    console.error('[MainProcess] FATAL ERROR: Preload script not found at:', preloadScriptPath);
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
    icon: path.join(__dirname, '../public/fac.ico') 
  });
  console.log('[MainProcess] BrowserWindow instance created.');

  Menu.setApplicationMenu(null);
  
  if (isServeMode) {
    const cspDirectives = [
      "default-src 'self' http://localhost:" + servePort, 
      "script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:" + servePort, 
      "style-src 'self' 'unsafe-inline'", 
      "img-src 'self' data: http://localhost:" + servePort + " http://127.0.0.1:*", 
      "font-src 'self' data: http://localhost:" + servePort, 
      "connect-src 'self' http://localhost:" + servePort + " http://127.0.0.1:*", 
      "media-src 'self' http://localhost:" + servePort + " http://127.0.0.1:*; ", 
      "object-src 'none'", 
      "frame-src 'none'"  
    ];
    const cspString = cspDirectives.join('; '); 

    console.log("[MainProcess] Applying CSP:", cspString);

    session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
      let responseHeaders = details.responseHeaders || {};
      responseHeaders['Content-Security-Policy'] = [cspString]; 
      callback({ responseHeaders });
    });

    const devUrl = `http://localhost:${servePort}`;
    console.log(`[MainProcess] Development mode, loading URL: ${devUrl}`);
    mainWindow.loadURL(devUrl)
      .then(() => {
        console.log(`[MainProcess] Successfully loaded URL: ${devUrl}`);
      })
      .catch(err => {
        console.error(`[MainProcess] Failed to load dev URL ${devUrl}:`, err);
        console.error(`[MainProcess] Please ensure Vite dev server is running on port ${servePort}.`);
      });
    mainWindow.webContents.openDevTools();
    console.log('[MainProcess] Developer tools opened in development mode.');
  } else {
    const indexHtmlPath = path.join(__dirname, '../dist/index.html');
    const indexPath = url.format({ pathname: indexHtmlPath, protocol: 'file:', slashes: true, });
    console.log(`[MainProcess] Production mode, loading file: ${indexPath}`);
     if (!fs.existsSync(indexHtmlPath)) {
        console.error('[MainProcess] ERROR: dist/index.html not found in production mode at path:', indexHtmlPath);
    }
    mainWindow.loadURL(indexPath)
      .then(() => console.log(`[MainProcess] Successfully loaded file: ${indexPath}`))
      .catch(err => console.error(`[MainProcess] Failed to load production file ${indexPath}:`, err));
  }

  mainWindow.on('closed', () => {
    console.log('[MainProcess] MainWindow closed.');
    mainWindow = null;
  });
}

app.whenReady().then(() => {
    console.log('[MainProcess] App is ready, calling createWindow.');
    createWindow();
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
        console.log('[MainProcess] App activated with no open windows, calling createWindow.');
        createWindow();
        }
    });
}).catch(err => {
  console.error('[MainProcess] Error during app.whenReady promise:', err);
});

app.on('window-all-closed', () => {
  console.log('[MainProcess] All windows closed.');
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('quit', () => {
  console.log('[MainProcess] App quitting.');
});

ipcMain.on('play-video-locally', (event, videoPath) => {
  if (videoPath && typeof videoPath === 'string') {
    console.log(`[MainProcess] IPC 'play-video-locally': Received request to play: ${videoPath}`);
    shell.openPath(videoPath)
      .then(() => console.log(`[MainProcess] IPC 'play-video-locally': Successfully attempted to open: ${videoPath}`))
      .catch(err => {
        console.error(`[MainProcess] IPC 'play-video-locally': Failed to open path "${videoPath}" using shell:`, err);
      });
  } else {
    console.error('[MainProcess] IPC \'play-video-locally\': Received invalid videoPath:', videoPath);
  }
});