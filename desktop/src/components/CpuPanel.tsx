import GlassPanel from './GlassPanel';
import Gauge from './Gauge';
import Sparkline from './Sparkline';
import ProgressBar from './ProgressBar';
import { useDashboardStore } from '@/store/dashboardStore';
import { useMemo } from 'react';

export default function CpuPanel() {
  const telemetry = useDashboardStore((s) => s.telemetry);
  const tempHistory = useDashboardStore((s) => s.tempHistory);
  const cpu = telemetry?.cpu;
  const cores = telemetry?.cpu_cores ?? [];
  const capability = telemetry?.capabilities?.cpu_hwmon;

  const sparkData = useMemo(
    () => tempHistory.map((p) => ({ time: p.time, value: p.cpu })),
    [tempHistory]
  );

  return (
    <GlassPanel
      title="CPU"
      accent="green"
      statusBadge={{ label: 'k10temp', active: capability?.available ?? false }}
    >
      <div className="flex items-start gap-4">
        <Gauge
          value={cpu?.temp_c ?? 0}
          max={100}
          size={80}
          label="TEMP"
          unit="°C"
        />
        <div className="flex-1 space-y-2">
          <div className="grid grid-cols-2 gap-1">
            <div className="text-[10px] text-gray-500">Frequency</div>
            <div className="text-[11px] font-mono text-neon-green text-right">
              {cpu?.current_freq_mhz != null ? `${(cpu.current_freq_mhz / 1000).toFixed(1)} GHz` : '---'}
            </div>
            <div className="text-[10px] text-gray-500">Limit</div>
            <div className="text-[11px] font-mono text-neon-cyan text-right">
              {cpu?.max_freq_mhz != null ? `${(cpu.max_freq_mhz / 1000).toFixed(1)} GHz` : '---'}
            </div>
            <div className="text-[10px] text-gray-500">Governor</div>
            <div className="text-[11px] font-mono text-neon-teal text-right">
              {cpu?.governor ?? '---'}
            </div>
          </div>
        </div>
      </div>

      {cores.length > 0 && (
        <div className="space-y-1 mt-1">
          {cores.slice(0, 8).map((freq, i) => (
            <ProgressBar
              key={i}
              value={freq / 1000}
              max={5300}
              label={`C${i}`}
              unit=" MHz"
            />
          ))}
        </div>
      )}

      <Sparkline data={sparkData} color="#00ff00" height={32} />
    </GlassPanel>
  );
}