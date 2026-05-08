import GlassPanel from './GlassPanel';
import { useDashboardStore } from '@/store/dashboardStore';

export default function BatteryPanel() {
  const telemetry = useDashboardStore((s) => s.telemetry);
  const battery = telemetry?.battery;
  const capability = telemetry?.capabilities?.battery;

  const pct = battery?.percent ?? 0;
  const color = pct > 50 ? '#00ff00' : pct > 20 ? '#ffff00' : '#ff4444';

  return (
    <GlassPanel
      title="Battery"
      accent="green"
      statusBadge={{ label: 'BAT0', active: capability?.available ?? false }}
    >
      <div className="flex items-center gap-4">
        <div className="relative inline-flex items-center justify-center">
          <svg width="80" height="80" className="transform -rotate-90">
            <circle cx="40" cy="40" r="32" fill="none" stroke="rgba(0,255,0,0.08)" strokeWidth="6" />
            <circle
              cx="40" cy="40" r="32"
              fill="none"
              stroke={color}
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 32}
              strokeDashoffset={2 * Math.PI * 32 * (1 - pct / 100)}
              style={{
                transition: 'stroke-dashoffset 0.6s ease, stroke 0.6s ease',
                filter: `drop-shadow(0 0 4px ${color})`,
              }}
            />
          </svg>
          <div className="absolute flex flex-col items-center">
            <span className="text-lg font-bold font-mono" style={{ color }}>
              {pct}
              <span className="text-xs">%</span>
            </span>
          </div>
        </div>

        <div className="flex-1 space-y-1">
          <div className="grid grid-cols-2 gap-1">
            <div className="text-[10px] text-gray-500">Status</div>
            <div className="text-[11px] font-mono text-neon-green text-right">
              {battery?.status ?? '---'}
            </div>
            <div className="text-[10px] text-gray-500">Power</div>
            <div className={`text-[11px] font-mono text-right ${
              (battery?.power_w ?? 0) > 0 ? 'text-neon-orange' : 'text-neon-green'
            }`}>
              {battery?.power_w != null ? `${battery.power_w.toFixed(1)} W` : '---'}
            </div>
          </div>
        </div>
      </div>
    </GlassPanel>
  );
}