import GlassPanel from './GlassPanel';
import Gauge from './Gauge';
import Sparkline from './Sparkline';
import { useDashboardStore } from '@/store/dashboardStore';
import { useMemo } from 'react';

export default function AmdGpuPanel() {
  const telemetry = useDashboardStore((s) => s.telemetry);
  const tempHistory = useDashboardStore((s) => s.tempHistory);
  const gpu = telemetry?.amd_gpu;
  const capability = telemetry?.capabilities?.amd_hwmon;

  const sparkData = useMemo(
    () => tempHistory.map((p) => ({ time: p.time, value: p.amd })),
    [tempHistory]
  );

  return (
    <GlassPanel
      title="AMD iGPU"
      accent="teal"
      statusBadge={{ label: 'amdgpu', active: capability?.available ?? false }}
    >
      <div className="flex items-start gap-4">
        <Gauge
          value={gpu?.temp_c ?? 0}
          max={105}
          size={80}
          label="TEMP"
          unit="°C"
        />
        <div className="flex-1 space-y-2">
          <div className="grid grid-cols-2 gap-1">
            <div className="text-[10px] text-gray-500">Clock</div>
            <div className="text-[11px] font-mono text-neon-teal text-right">
              {gpu?.clock_mhz != null ? `${gpu.clock_mhz} MHz` : '---'}
            </div>
            <div className="text-[10px] text-gray-500">Power</div>
            <div className="text-[11px] font-mono text-neon-teal text-right">
              {gpu?.power_w != null ? `${gpu.power_w.toFixed(2)} W` : '---'}
            </div>
          </div>
        </div>
      </div>
      <Sparkline data={sparkData} color="#00cc88" height={32} />
    </GlassPanel>
  );
}