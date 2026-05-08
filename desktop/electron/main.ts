import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';
import { PythonBridge } from './pythonBridge';

let mainWindow: BrowserWindow | null = null;
let pythonBridge: PythonBridge | null = null;

function createWindow(url: string) {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    frame: true,
    titleBarStyle: 'default',
    backgroundColor: '#0a0a0f',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL(url);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  pythonBridge = new PythonBridge();

  pythonBridge.on('data', (payload) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('telemetry', payload);
    }
  });

  pythonBridge.on('status', (status) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('backend-status', status);
    }
  });

  // Always start Python server
  pythonBridge.start();

  // Use built files for now (simpler than Vite dev server)
  const indexPath = path.join(__dirname, '../dist/index.html');
  createWindow(`file://${indexPath}`);

  ipcMain.handle('send-command', async (_event, command: any) => {
    try {
      await pythonBridge?.sendCommand(command);
      return { success: true };
    } catch (err: any) {
      return { success: false, message: err.message };
    }
  });

  ipcMain.handle('get-backend-status', () => {
    return pythonBridge?.connected ?? false;
  });
});

app.on('window-all-closed', () => {
  pythonBridge?.stop();
  app.quit();
});

app.on('before-quit', () => {
  pythonBridge?.stop();
});