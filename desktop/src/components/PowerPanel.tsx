import GlassPanel from './GlassPanel';
import ProgressBar from './ProgressBar';
import { useDashboardStore } from '@/store/dashboardStore';

const powerColor = (pct: number) => {
  if (pct >= 90) return '#ff4444';
  if (pct >= 75) return '#ffff00';
  if (pct >= 50) return '#ffaa00';
  return '#00ff00';
};

export default function PowerPanel() {
  const telemetry = useDashboardStore((s) => s.telemetry);
  const info = telemetry?.power_info;

  return (
    <GlassPanel title="Power (RyzenAdj)" accent="orange">
      {info?.stapm_limit ? (
        <div className="space-y-1">
          <ProgressBar
            value={info.stapm_value ?? 0}
            max={info.stapm_limit}
            label="STAPM"
            unit="W"
            colorFn={powerColor}
          />
          <ProgressBar
            value={info.fast_value ?? 0}
            max={info.fast_limit ?? 100}
            label="Fast PPT"
            unit="W"
            colorFn={powerColor}
          />
          <ProgressBar
            value={info.slow_value ?? 0}
            max={info.slow_limit ?? 100}
            label="Slow PPT"
            unit="W"
            colorFn={powerColor}
          />
          <div className="grid grid-cols-2 gap-1 mt-2">
            <div className="text-[10px] text-gray-500">Thermal Limit</div>
            <div className="text-[11px] font-mono text-neon-orange text-right">
              {info.tctl_value != null ? `${info.tctl_value.toFixed(0)}°C` : '---'}
            </div>
            <div className="text-[10px] text-gray-500">VRM Current</div>
            <div className="text-[11px] font-mono text-neon-orange text-right">
              {info.vrm_current != null ? `${info.vrm_current.toFixed(1)}A` : '---'}
            </div>
          </div>
        </div>
      ) : (
        <div className="text-[11px] text-gray-500 text-center py-4">ryzenadj not available</div>
      )}
    </GlassPanel>
  );
}