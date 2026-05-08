import { contextBridge, ipcRenderer } from 'electron';

const listeners = new Map<string, (event: any, ...args: any[]) => void>();

function addListener(channel: string, callback: (...args: any[]) => void) {
  const wrapped = (_event: any, ...args: any[]) => callback(...args);
  listeners.set(channel, wrapped);
  ipcRenderer.on(channel, wrapped);
}

contextBridge.exposeInMainWorld('rogAPI', {
  onTelemetry: (callback: (data: any) => void) => {
    addListener('telemetry', (_event, data) => callback(data));
  },
  onBackendStatus: (callback: (status: any) => void) => {
    addListener('backend-status', (_event, status) => callback(status));
  },
  sendCommand: (command: any) => {
    return ipcRenderer.invoke('send-command', command);
  },
  getBackendStatus: () => {
    return ipcRenderer.invoke('get-backend-status');
  },
});
