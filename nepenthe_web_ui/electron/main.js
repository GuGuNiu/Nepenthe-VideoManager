import { app, BrowserWindow, ipcMain, shell, Menu, session, dialog } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import url from "node:url";
import Store from "electron-store";
import { spawn, execSync } from "node:child_process";
import net from "node:net";

const defaultConfig = {
  apiHost: "127.0.0.1",
  apiPort: 8000,
  internalApiHost: "127.0.0.1",
  internalApiPort: 28000,
  videoPaths: [],
  ffmpegPath: "",
  ffprobePath: "",
  windowWidth: 1600,
  windowHeight: 900,
  windowX: undefined,
  windowY: undefined,
};
const store = new Store({ defaults: defaultConfig });

let dataDirRootForApp;
let dbFilePath;
let thumbnailsStoragePath;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const cliArgs = process.argv.slice(1);
const isServeMode = cliArgs.includes("--serve") && !app.isPackaged;
let viteServePort = 5174;
const portArgIndexCLI = cliArgs.indexOf("--port");
if (portArgIndexCLI !== -1 && cliArgs[portArgIndexCLI + 1]) {
  const parsedPort = parseInt(cliArgs[portArgIndexCLI + 1], 10);
  if (!isNaN(parsedPort)) {
    viteServePort = parsedPort;
  }
}

let mainWindow;
let pythonBackendProcess = null;
let backendJustClosedManually = false;
let backendApiUrl = "";

function logToConsole(level, ...args) {
  const message = args.map((arg) => (typeof arg === "object" ? JSON.stringify(arg) : String(arg))).join(" ");
  const timestamp = new Date().toISOString();
  console[level](`[${timestamp}] [MainProcess-${level.toUpperCase()}] ${message}`);
}

function initializeEssentialPaths() {
  try {
    if (app.isPackaged) {
      dataDirRootForApp = path.join(path.dirname(app.getPath("exe")), "data");
      logToConsole("info", `Packaged mode. App data root set to: ${dataDirRootForApp}`);
    } else {
      const mainProjectRootDev = path.resolve(app.getAppPath(), "..");
      dataDirRootForApp = path.join(mainProjectRootDev, "data");
      logToConsole("info", `Development mode. App data root set to: ${dataDirRootForApp}`);
    }
    if (!fs.existsSync(dataDirRootForApp)) {
      fs.mkdirSync(dataDirRootForApp, { recursive: true });
    }
    dbFilePath = path.join(dataDirRootForApp, "nepenthe_videos.db");
    thumbnailsStoragePath = path.join(dataDirRootForApp, "thumbnails");
    if (!fs.existsSync(thumbnailsStoragePath)) {
      fs.mkdirSync(thumbnailsStoragePath, { recursive: true });
    }
    logToConsole("info", `DB file path: ${dbFilePath}`);
    logToConsole("info", `Thumbnails storage path: ${thumbnailsStoragePath}`);
    return true;
  } catch (error) {
    logToConsole("error", `FATAL ERROR initializing app data paths: ${error.message}`, error.stack);
    dialog.showErrorBox("Data Path Error", `Failed to initialize application data paths.\nError: ${error.message}`);
    app.quit();
    return false;
  }
}

function getPythonBackendExePath() {
  const backendExecutableName = process.platform === "win32" ? "nepenthe_backend.exe" : "nepenthe_backend";
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "assets", "backend", backendExecutableName);
  } else {
    return path.resolve(app.getAppPath(), "dev_backend", "nepenthe_backend", backendExecutableName);
  }
}

async function findFreePort(startPort = 28000) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(startPort, "127.0.0.1", () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
    server.on("error", (err) => {
      if (err.code === "EADDRINUSE" || err.code === "EACCES") {
        resolve(findFreePort(startPort + 1));
      } else {
        reject(err);
      }
    });
  });
}

async function startPythonBackend() {
  if (pythonBackendProcess && pythonBackendProcess.pid && !pythonBackendProcess.killed) {
    logToConsole("warn", `Python backend (PID: ${pythonBackendProcess.pid}) is already running.`);
    if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed() && backendApiUrl) {
      mainWindow.webContents.send("backend-status-update", { status: "running", apiUrl: backendApiUrl });
    }
    return store.get("internalApiPort");
  }

  const backendExePath = getPythonBackendExePath();
  if (!backendExePath || !fs.existsSync(backendExePath)) {
    const errorMsg = `Python backend executable not found at: ${backendExePath || "path not determined"}`;
    logToConsole("error", errorMsg);
    dialog.showErrorBox("Backend Error", errorMsg);
    if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed())
      mainWindow.webContents.send("backend-status-update", { status: "error", message: "Backend executable not found" });
    return null;
  }

  const apiHostForBackend = "127.0.0.1";
  let actualApiPortForBackend;
  try {
    actualApiPortForBackend = await findFreePort(store.get("internalApiPort", defaultConfig.internalApiPort));
  } catch (portError) {
    logToConsole("error", "Could not find a free port for the backend:", portError.message);
    dialog.showErrorBox("Backend Port Error", `Could not find an available port for the backend.\n${portError.message}`);
    if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed())
      mainWindow.webContents.send("backend-status-update", { status: "error", message: "No available port for backend" });
    return null;
  }

  store.set("internalApiHost", apiHostForBackend);
  store.set("internalApiPort", actualApiPortForBackend);
  backendApiUrl = `http://${apiHostForBackend}:${actualApiPortForBackend}`;

  const videoPathsFromStore = store.get("videoPaths", []);
  const ffmpegPathFromStore = store.get("ffmpegPath", "");
  const ffprobePathFromStore = store.get("ffprobePath", "");

  const backendArgs = ["--host", apiHostForBackend, "--port", actualApiPortForBackend.toString(), "--db-file-path", dbFilePath, "--thumbnails-storage-path", thumbnailsStoragePath];
  if (videoPathsFromStore && videoPathsFromStore.length > 0) backendArgs.push("--video_paths", videoPathsFromStore.join(","));
  if (ffmpegPathFromStore) backendArgs.push("--ffmpeg-path", ffmpegPathFromStore);
  if (ffprobePathFromStore) backendArgs.push("--ffprobe-path", ffprobePathFromStore);

  logToConsole("info", `Starting Python backend: ${backendExePath} with args: ${backendArgs.join(" ")}`);
  if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) {
    mainWindow.webContents.send("backend-status-update", { status: "starting", apiUrl: backendApiUrl });
  }

  try {
    const backendWorkingDirectory = path.dirname(backendExePath);
    pythonBackendProcess = spawn(backendExePath, backendArgs, {
      stdio: "ignore",
      cwd: backendWorkingDirectory,
      windowsHide: true,
    });

    if (!pythonBackendProcess || !pythonBackendProcess.pid) {
      throw new Error("Failed to spawn backend process (process or PID is null).");
    }
    backendJustClosedManually = false;

    pythonBackendProcess.on("error", (err) => {
      logToConsole("error", `Failed to start Python backend process (spawn error): ${err.message}`, err.stack);
      if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed())
        mainWindow.webContents.send("backend-status-update", { status: "error", message: `Failed to start Python backend: ${err.message}` });
      pythonBackendProcess = null;
    });
    pythonBackendProcess.on("close", (code, signal) => {
      const pidForLog = pythonBackendProcess ? pythonBackendProcess.pid : "N/A (already null)";
      if (!backendJustClosedManually) {
        logToConsole("warn", `Python backend process (PID: ${pidForLog}) closed unexpectedly or finished. Code: ${code}, Signal: ${signal}`);
        if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) {
          mainWindow.webContents.send("backend-status-update", { status: "stopped", message: `Backend process exited with code ${code}.` });
        }
      } else {
        logToConsole("info", `Python backend process (PID: ${pidForLog}) closed after manual termination. Code: ${code}, Signal: ${signal}`);
      }
      pythonBackendProcess = null;
      backendApiUrl = "";
    });
    logToConsole("info", `Python backend process spawned (PID: ${pythonBackendProcess.pid}), should listen on ${backendApiUrl}`);

    if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) {
      setTimeout(() => {
        if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed() && pythonBackendProcess && !pythonBackendProcess.killed) {
          mainWindow.webContents.send("backend-status-update", { status: "running", apiUrl: backendApiUrl });
        }
      }, 2000);
    }
    return actualApiPortForBackend;
  } catch (spawnError) {
    logToConsole("error", "Exception while spawning Python backend process:", spawnError.message, spawnError.stack);
    if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed())
      mainWindow.webContents.send("backend-status-update", { status: "error", message: `Error spawning Python backend: ${spawnError.message}` });
    pythonBackendProcess = null;
    return null;
  }
}

async function stopPythonBackend() {
  return new Promise((resolve) => {
    if (!pythonBackendProcess || pythonBackendProcess.killed) {
      logToConsole("info", "Backend process is not running or already killed.");
      if (pythonBackendProcess) pythonBackendProcess = null;
      resolve();
      return;
    }
    const pid = pythonBackendProcess.pid;
    logToConsole("info", `Attempting to stop backend process (PID: ${pid})...`);
    backendJustClosedManually = true;
    let resolved = false;
    const resolveOnce = () => {
      if (!resolved) {
        resolved = true;
        pythonBackendProcess = null;
        backendApiUrl = "";
        resolve();
      }
    };
    const killTimeout = setTimeout(() => {
      logToConsole("warn", `Backend process (PID: ${pid}) did not exit within timeout. Forcing kill.`);
      if (pythonBackendProcess && !pythonBackendProcess.killed) {
        if (process.platform === "win32") {
          try {
            execSync(`taskkill /PID ${pid} /F /T`, { stdio: "ignore" });
            logToConsole("info", `Forced kill (taskkill /F /T) command issued for PID ${pid}.`);
          } catch (e_force) {
            let forceKillErrorMessage = `Forced taskkill for PID ${pid} failed.`;
            if (e_force.status) {
              forceKillErrorMessage += ` Exit status: ${e_force.status}.`;
            }
            if (e_force.status === 128) {
              forceKillErrorMessage += " Reason: Process not found (it may have already exited).";
            } else if (e_force.status === 1) {
              forceKillErrorMessage += " Reason: Operation failed (e.g., access denied or process cannot be terminated).";
            } else if (e_force.status !== null && e_force.status !== undefined) {
              forceKillErrorMessage += " Reason: taskkill command failed with a non-zero exit code.";
            } else {
              forceKillErrorMessage += ` execSync error: ${e_force.message}`;
            }
            logToConsole("error", forceKillErrorMessage);
          }
        } else {
          pythonBackendProcess.kill("SIGKILL");
          logToConsole("info", `Sent SIGKILL to PID ${pid}.`);
        }
      }
      resolveOnce();
    }, 7000);
    pythonBackendProcess.once("close", (code, signal) => {
      clearTimeout(killTimeout);
      logToConsole("info", `Backend process (PID: ${pid}) confirmed exit. Code: ${code}, Signal: ${signal}.`);
      resolveOnce();
    });
    if (process.platform === "win32") {
      try {
        execSync(`taskkill /PID ${pid} /T`, { stdio: "ignore" });
        logToConsole("info", `Gentle taskkill (/T) command issued for PID ${pid}. Waiting for process to close.`);
      } catch (e) {
        let gentleKillErrorMessage = `Gentle taskkill (/T) for PID ${pid} failed.`;
        if (e.status) {
          gentleKillErrorMessage += ` Exit status: ${e.status}.`;
        }
        if (e.status === 128) {
          gentleKillErrorMessage += " Reason: Process could not be terminated gracefully (e.g., child processes running or process not found).";
        } else if (e.status === 1) {
          gentleKillErrorMessage += " Reason: Operation failed (e.g., access denied).";
        } else if (e.status !== null && e.status !== undefined) {
          gentleKillErrorMessage += " Reason: taskkill command failed with a non-zero exit code.";
        } else {
          gentleKillErrorMessage += ` execSync error: ${e.message}`;
        }
        logToConsole("warn", gentleKillErrorMessage);
      }
    } else {
      const success = pythonBackendProcess.kill("SIGTERM");
      if (success) {
        logToConsole("info", `Sent SIGTERM to PID ${pid}. Waiting for process to close.`);
      } else {
        logToConsole("warn", `Failed to send SIGTERM to PID ${pid} (process might have already exited).`);
        clearTimeout(killTimeout);
        resolveOnce();
      }
    }
  });
}

async function createWindow() {
  const preloadScriptPath = path.join(__dirname, "preload.js");
  if (!fs.existsSync(preloadScriptPath)) {
    logToConsole("error", "FATAL ERROR: Preload script not found at:", preloadScriptPath);
    app.quit();
    return;
  }
  mainWindow = new BrowserWindow({
    width: store.get("windowWidth"),
    height: store.get("windowHeight"),
    minWidth: 1000,
    minHeight: 600,
    x: store.get("windowX"),
    y: store.get("windowY"),
    webPreferences: { preload: preloadScriptPath, contextIsolation: true, nodeIntegration: false, devTools: isServeMode },
    icon: path.join(__dirname, "../public/fac.ico"),
  });
  mainWindow.on("resized", () => {
    if (mainWindow && !mainWindow.isMinimized() && !mainWindow.isMaximized()) {
      const [width, height] = mainWindow.getSize();
      store.set("windowWidth", width);
      store.set("windowHeight", height);
    }
  });
  mainWindow.on("moved", () => {
    if (mainWindow && !mainWindow.isMinimized() && !mainWindow.isMaximized()) {
      const [x, y] = mainWindow.getPosition();
      store.set("windowX", x);
      store.set("windowY", y);
    }
  });
  const winX = store.get("windowX");
  const winY = store.get("windowY");
  if (typeof winX === "number" && typeof winY === "number") mainWindow.setPosition(winX, winY);
  Menu.setApplicationMenu(null);
  const backendPort = await startPythonBackend();
  let apiHostForFrontend = store.get("internalApiHost");
  let apiPortForFrontend = store.get("internalApiPort");
  if (!backendPort) {
    logToConsole("error", "CRITICAL: Python backend failed to start. Frontend might not work correctly.");
    apiHostForFrontend = store.get("apiHost", defaultConfig.apiHost);
    apiPortForFrontend = store.get("apiPort", defaultConfig.apiPort);
    logToConsole("warn", `Falling back to general API config for frontend: http://${apiHostForFrontend}:${apiPortForFrontend}`);
    dialog.showErrorBox("Backend Failed", "The backend service could not be started. Please check logs or restart the application.");
  }
  const dynamicApiOrigin = `http://${apiHostForFrontend}:${apiPortForFrontend}`;
  logToConsole("info", "API Origin for CSP and Preload:", dynamicApiOrigin);
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const cspDirectives = [
      `default-src 'self' http://localhost:${viteServePort}`,
      `script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:${viteServePort}`,
      `style-src 'self' 'unsafe-inline'`,
      `img-src 'self' data: blob: http://localhost:${viteServePort} ${dynamicApiOrigin}`,
      `font-src 'self' data: http://localhost:${viteServePort}`,
      `connect-src 'self' http://localhost:${viteServePort} ${dynamicApiOrigin} ws://localhost:${viteServePort}`,
      `media-src 'self' data: blob: http://localhost:${viteServePort} ${dynamicApiOrigin}`,
      `object-src 'none'`,
      `frame-src 'none'`,
    ];
    const cspString = cspDirectives.map((d) => (d.trim().endsWith(";") ? d.trim() : d.trim() + ";")).join(" ");
    callback({ responseHeaders: { ...details.responseHeaders, "Content-Security-Policy": [cspString] } });
  });
  if (isServeMode) {
    const devUrl = `http://localhost:${viteServePort}`;
    mainWindow
      .loadURL(devUrl)
      .then(() => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.focus();
          if (!mainWindow.webContents.isDevToolsOpened()) mainWindow.webContents.openDevTools({ mode: "detach" });
        }
      })
      .catch((err) => logToConsole("error", `Failed to load dev URL ${devUrl}: ${err.message}`, err.stack));
  } else {
    const indexHtmlPath = path.join(__dirname, "../dist/index.html");
    const indexPath = url.format({ pathname: indexHtmlPath, protocol: "file:", slashes: true });
    if (!fs.existsSync(indexHtmlPath)) {
      logToConsole("error", "ERROR: Production build (dist/index.html) not found at:", indexHtmlPath);
      dialog.showErrorBox("Application Error", "The application files (index.html) could not be found.");
      app.quit();
      return;
    }
    mainWindow
      .loadURL(indexPath)
      .then(() => {
        if (mainWindow && !mainWindow.isDestroyed()) mainWindow.focus();
      })
      .catch((err) => logToConsole("error", `Failed to load production file ${indexPath}: ${err.message}`, err.stack));
  }
  mainWindow.webContents.on("devtools-closed", () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.focus();
      setTimeout(() => {
        if (mainWindow && !mainWindow.isDestroyed()) mainWindow.focus();
      }, 100);
    }
  });
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

ipcMain.handle("get-all-configs", () => {
  return {
    apiHost: store.get("internalApiHost", defaultConfig.internalApiHost),
    apiPort: store.get("internalApiPort", defaultConfig.internalApiPort),
    videoPaths: store.get("videoPaths", defaultConfig.videoPaths),
    ffmpegPath: store.get("ffmpegPath", defaultConfig.ffmpegPath),
    ffprobePath: store.get("ffprobePath", defaultConfig.ffprobePath),
    isPackaged: app.isPackaged,
  };
});
ipcMain.handle("get-config", (event, key) => store.get(key));
ipcMain.handle("set-config", (event, key, value) => {
  try {
    store.set(key, value);
    logToConsole("info", `Config set: ${key} = ${JSON.stringify(value)}`);
    return { success: true };
  } catch (error) {
    logToConsole("error", `Failed to set config: ${key}`, error.message, error.stack);
    return { success: false, error: error.message };
  }
});
ipcMain.handle("get-platform", () => process.platform);
ipcMain.handle("browse-directory", async () => {
  const tWin = BrowserWindow.getFocusedWindow() || mainWindow;
  if (!tWin || tWin.isDestroyed()) return null;
  const r = await dialog.showOpenDialog(tWin, { properties: ["openDirectory"] });
  if (!r.canceled && r.filePaths.length > 0) return r.filePaths[0];
  return null;
});
ipcMain.handle("browse-file", async (event, options) => {
  const tWin = BrowserWindow.getFocusedWindow() || mainWindow;
  if (!tWin || tWin.isDestroyed()) return null;
  const o = { properties: ["openFile"], title: options?.title || "选择文件", filters: options?.filters || [{ name: "所有文件", extensions: ["*"] }] };
  const r = await dialog.showOpenDialog(tWin, o);
  if (!r.canceled && r.filePaths.length > 0) return r.filePaths[0];
  return null;
});
ipcMain.on("play-video-locally", (event, videoPath) => {
  if (videoPath && typeof videoPath === "string") {
    shell.openPath(videoPath).catch((err) => logToConsole("error", `IPC play-video-locally error: ${err.message}`));
  } else {
    logToConsole("error", "IPC play-video-locally: invalid videoPath");
  }
});
ipcMain.on("show-item-in-folder", (event, itemPath) => {
  if (itemPath && typeof itemPath === "string") {
    shell.showItemInFolder(itemPath);
  } else {
    logToConsole("error", "IPC show-item-in-folder: invalid itemPath");
  }
});
ipcMain.on("open-external-link", (event, extUrl) => {
  if (extUrl && (extUrl.startsWith("http:") || extUrl.startsWith("https:"))) {
    shell.openExternal(extUrl).catch((err) => logToConsole("error", `IPC open-external-link error: ${err.message}`));
  }
});
ipcMain.handle("get-app-version", () => app.getVersion());
ipcMain.handle("check-initial-config-status", () => ({ needsSetup: !store.get("videoPaths", []).length }));
ipcMain.handle("start-python-backend-manual", async () => {
  logToConsole("info", "IPC: Manual backend start requested.");
  const port = await startPythonBackend();
  return { success: !!port, port: port, host: store.get("internalApiHost") };
});
ipcMain.handle("stop-python-backend-manual", async () => {
  logToConsole("info", "IPC: Manual backend stop requested.");
  await stopPythonBackend();
  return { success: true };
});

app
  .whenReady()
  .then(async () => {
    if (!initializeEssentialPaths()) {
      logToConsole("error", "Failed to initialize essential paths. Application will quit.");
      return;
    }
    await createWindow();
    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  })
  .catch((err) => logToConsole("error", "Error during app.whenReady:", err.message, err.stack));

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("will-quit", async (event) => {
  logToConsole("info", "'will-quit' event triggered. Preparing to stop backend...");
  event.preventDefault();
  try {
    await stopPythonBackend();
    logToConsole("info", "Backend stopped. Proceeding with app quit.");
  } catch (error) {
    logToConsole("error", "Error stopping backend during app quit:", error.message, error.stack);
  } finally {
    app.exit();
  }
});
