const { app, BrowserWindow, Menu, globalShortcut, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

const projectRoot = path.resolve(__dirname, '..');
let mainWindow = null;
let backendProcess = null;
let ownsBackend = false;

function getPythonCommand() {
  if (process.env.PYTHON) return { command: process.env.PYTHON, prefixArgs: [] };

  const windowsPython = path.join(projectRoot, '.venv', 'Scripts', 'python.exe');
  const unixPython = path.join(projectRoot, '.venv', 'bin', 'python');
  const candidate = process.platform === 'win32' ? windowsPython : unixPython;
  const fs = require('fs');
  if (fs.existsSync(candidate)) return { command: candidate, prefixArgs: [] };
  return { command: process.platform === 'win32' ? 'python' : 'python3', prefixArgs: [] };
}

function checkBackend() {
  return new Promise((resolve) => {
    const request = http.get('http://127.0.0.1:8765/api/health', (response) => {
      response.resume();
      resolve(response.statusCode === 200);
    });
    request.setTimeout(700, () => request.destroy());
    request.on('error', () => resolve(false));
  });
}

async function startBackend() {
  if (await checkBackend()) {
    console.log('Using an existing local Mesa service.');
    return;
  }

  const python = getPythonCommand();
  const entry = path.join(projectRoot, 'electron_backend', 'server.py');
  backendProcess = spawn(python.command, [...python.prefixArgs, entry], {
    cwd: projectRoot,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  });
  ownsBackend = true;
  backendProcess.stdout.on('data', (chunk) => console.log(`[Mesa] ${chunk.toString().trimEnd()}`));
  backendProcess.stderr.on('data', (chunk) => console.error(`[Mesa] ${chunk.toString().trimEnd()}`));
  backendProcess.on('error', (error) => {
    console.error('Could not launch the Python Mesa service:', error);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('backend-error', error.message);
    }
  });
  backendProcess.on('exit', (code) => {
    if (code && mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('backend-error', `The analysis service stopped (exit code ${code}).`);
    }
  });

  // Wait for Mesa and the trained screener to initialize without freezing the UI.
  for (let attempt = 0; attempt < 80; attempt += 1) {
    if (await checkBackend()) return;
    if (backendProcess && backendProcess.exitCode !== null) break;
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error('The local Mesa service did not become ready. Check Python and the requirements.');
}

function createWindow() {
  Menu.setApplicationMenu(null);
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 960,
    minHeight: 650,
    show: false,
    fullscreen: false,
    autoHideMenuBar: true,
    backgroundColor: '#f4f7ff',
    title: 'MindSpring',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.maximize();
  });
  mainWindow.on('closed', () => { mainWindow = null; });
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
}

app.whenReady().then(async () => {
  try {
    await startBackend();
    createWindow();
  } catch (error) {
    dialog.showErrorBox(
      'MindSpring could not start',
      `${error.message}\n\nInstall the Python packages from the project requirements.txt, then launch MindSpring again.`
    );
    app.quit();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
  globalShortcut.register('F11', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.setFullScreen(!mainWindow.isFullScreen());
    }
  });
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  if (ownsBackend && backendProcess && !backendProcess.killed) backendProcess.kill();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
