import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('rogAPI', {
  onTelemetry: (callback: (data: any) => void) => {
    ipcRenderer.on('telemetry', (_event, data) => callback(data));
  },
  onBackendStatus: (callback: (status: any) => void) => {
    ipcRenderer.on('backend-status', (_event, status) => callback(status));
  },
  sendCommand: (command: object) => {
    return ipcRenderer.invoke('send-command', command);
  },
  getBackendStatus: () => {
    return ipcRenderer.invoke('get-backend-status');
  },
});