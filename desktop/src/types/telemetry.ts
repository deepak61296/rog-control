export interface CPUStats {
  temp_c: number | null;
  current_freq_mhz: number | null;
  max_freq_mhz: number | null;
  governor: string | null;
}

export interface AMDGPUStats {
  temp_c: number | null;
  clock_mhz: number | null;
  power_w: number | null;
}

export interface NvidiaGPUStats {
  temp_c: number | null;
  power_w: number | null;
  clock_mhz: number | null;
  util_percent: number | null;
  vram_used_mb: number | null;
  vram_total_mb: number | null;
}

export interface CoolingStats {
  cpu_fan_rpm: number | null;
  gpu_fan_rpm: number | null;
}

export interface BatteryStats {
  percent: number | null;
  power_w: number | null;
  status: string | null;
}

export interface Capability {
  available: boolean;
  reason: string;
  last_error: string;
}

export interface PowerInfo {
  stapm_limit: number | null;
  stapm_value: number | null;
  fast_limit: number | null;
  fast_value: number | null;
  slow_limit: number | null;
  slow_value: number | null;
  tctl_limit: number | null;
  tctl_value: number | null;
  vrm_current: number | null;
  vrm_current_limit: number | null;
  vrm_max_current: number | null;
  vrm_max_current_limit: number | null;
}

export interface TelemetryPayload {
  type: 'telemetry';
  cpu: CPUStats;
  amd_gpu: AMDGPUStats;
  nvidia_gpu: NvidiaGPUStats;
  cooling: CoolingStats;
  battery: BatteryStats;
  nvme_temp_c: number | null;
  capabilities: Record<string, Capability>;
  errors: string[];
  power_info: PowerInfo;
  fan_profile: string | null;
  custom_curve_enabled: boolean | null;
  cpu_cores: number[];
}

export interface CommandResult {
  type: 'result';
  success: boolean;
  message: string;
}

export interface BackendStatus {
  connected: boolean;
}

export interface ROGAPI {
  onTelemetry: (callback: (data: TelemetryPayload) => void) => void;
  onBackendStatus: (callback: (status: BackendStatus) => void) => void;
  sendCommand: (command: object) => Promise<{ success: boolean; message?: string }>;
  getBackendStatus: () => Promise<boolean>;
}

declare global {
  interface Window {
    rogAPI?: ROGAPI;
  }
}