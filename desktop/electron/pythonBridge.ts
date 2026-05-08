import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import WebSocket from 'ws';
import path from 'path';

const SERVER_SCRIPT = path.join(__dirname, '../../../src/server.py');
const WS_URL = 'ws://127.0.0.1:9876';

export class PythonBridge extends EventEmitter {
  private process: ChildProcess | null = null;
  private ws: WebSocket | null = null;
  private _connected = false;
  private reconnectTimer: NodeJS.Timeout | null = null;

  get connected() {
    return this._connected;
  }

  start() {
    const pythonCmd = process.env.PYTHON_PATH || 'python3';
    this.process = spawn(pythonCmd, [SERVER_SCRIPT], {
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    });

    this.process.stdout?.on('data', (data: Buffer) => {
      console.log('[python]', data.toString().trim());
    });

    this.process.stderr?.on('data', (data: Buffer) => {
      console.error('[python:err]', data.toString().trim());
    });

    this.process.on('exit', (code) => {
      console.log(`Python server exited with code ${code}`);
      this._connected = false;
      this.emit('status', { connected: false });
      this.scheduleReconnect();
    });

    setTimeout(() => this.connectWS(), 1000);
  }

  private connectWS() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.ws = new WebSocket(WS_URL);

    this.ws.on('open', () => {
      console.log('WebSocket connected to Python server');
      this._connected = true;
      this.emit('status', { connected: true });
    });

    this.ws.on('message', (raw: WebSocket.Data) => {
      try {
        const payload = JSON.parse(raw.toString());
        this.emit('data', payload);
      } catch {
        // ignore parse errors
      }
    });

    this.ws.on('close', () => {
      this._connected = false;
      this.emit('status', { connected: false });
      this.scheduleReconnect();
    });

    this.ws.on('error', (err: Error) => {
      console.error('WebSocket error:', err.message);
    });
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connectWS();
    }, 3000);
  }

  async sendCommand(command: object): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('Backend not connected');
    }
    this.ws.send(JSON.stringify(command));
  }

  stop() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.process) {
      this.process.kill('SIGTERM');
      setTimeout(() => {
        if (this.process && !this.process.killed) {
          this.process.kill('SIGKILL');
        }
      }, 3000);
      this.process = null;
    }
  }
}