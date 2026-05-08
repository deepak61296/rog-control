import { create } from 'zustand';
import type { TelemetryPayload, BackendStatus } from '@/types/telemetry';

interface DashboardState {
  telemetry: TelemetryPayload | null;
  backendConnected: boolean;
  lastError: string | null;
  tempHistory: { time: number; cpu: number; amd: number; nvidia: number }[];
  setTelemetry: (data: TelemetryPayload) => void;
  setBackendStatus: (status: BackendStatus) => void;
  setLastError: (error: string) => void;
  sendCommand: (action: string, params?: Record<string, any>) => Promise<string>;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  telemetry: null,
  backendConnected: false,
  lastError: null,
  tempHistory: [],

  setTelemetry: (data: TelemetryPayload) => {
    const now = Date.now();
    const cpu = data.cpu.temp_c ?? 0;
    const amd = data.amd_gpu.temp_c ?? 0;
    const nvidia = data.nvidia_gpu.temp_c ?? 0;

    set((state) => ({
      telemetry: data,
      tempHistory: [
        ...state.tempHistory.slice(-59),
        { time: now, cpu, amd, nvidia },
      ],
      lastError: data.errors.length > 0 ? data.errors[0] : null,
    }));
  },

  setBackendStatus: (status: BackendStatus) => {
    set({ backendConnected: status.connected });
  },

  setLastError: (error: string) => {
    set({ lastError: error });
  },

  sendCommand: async (action: string, params: Record<string, any> = {}) => {
    const api = window.rogAPI;
    if (!api) return 'API not available (running in browser)';

    const result = await api.sendCommand({ action, ...params });
    return result.success ? 'OK' : result.message || 'Failed';
  },
}));