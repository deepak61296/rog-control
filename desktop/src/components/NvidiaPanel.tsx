import GlassPanel from './GlassPanel';
import Gauge from './Gauge';
import ProgressBar from './ProgressBar';
import { useDashboardStore } from '@/store/dashboardStore';

export default function NvidiaPanel() {
  const telemetry = useDashboardStore((s) => s.telemetry);
  const gpu = telemetry?.nvidia_gpu;
  const capability = telemetry?.capabilities?.nvidia;

  return (
    <GlassPanel
      title="NVIDIA dGPU"
      accent="cyan"
      statusBadge={{ label: 'nvidia-smi', active: capability?.available ?? false }}
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
            <div className="text-[11px] font-mono text-neon-cyan text-right">
              {gpu?.clock_mhz != null ? `${gpu.clock_mhz} MHz` : '---'}
            </div>
            <div className="text-[10px] text-gray-500">Power</div>
            <div className="text-[11px] font-mono text-neon-cyan text-right">
              {gpu?.power_w != null ? `${gpu.power_w.toFixed(1)} W` : '---'}
            </div>
            <div className="text-[10px] text-gray-500">VRAM</div>
            <div className="text-[11px] font-mono text-neon-cyan text-right">
              {gpu?.vram_used_mb != null ? `${gpu.vram_used_mb}/${gpu.vram_total_mb} MB` : '---'}
            </div>
          </div>
        </div>
      </div>

      <ProgressBar
        value={gpu?.util_percent ?? 0}
        max={100}
        label="Util"
        unit="%"
      />
      {gpu?.vram_total_mb != null && gpu?.vram_used_mb != null && (
        <ProgressBar
          value={gpu.vram_used_mb}
          max={gpu.vram_total_mb}
          label="VRAM"
          unit=" MB"
        />
      )}
    </GlassPanel>
  );
}