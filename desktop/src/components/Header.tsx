import { useDashboardStore } from '@/store/dashboardStore';

export default function Header() {
  const connected = useDashboardStore((s) => s.backendConnected);
  const telemetry = useDashboardStore((s) => s.telemetry);

  const caps = telemetry?.capabilities ?? {};
  const badges = [
    { label: 'CPU', active: caps.cpu_hwmon?.available },
    { label: 'AMD', active: caps.amd_hwmon?.available },
    { label: 'NVIDIA', active: caps.nvidia?.available },
    { label: 'RyzenAdj', active: !!telemetry?.power_info?.stapm_limit },
    { label: 'asusctl', active: !!telemetry?.fan_profile },
    { label: 'BAT', active: caps.battery?.available },
  ];

  return (
    <header className="glass-strong px-6 py-3 flex items-center justify-between border-b border-neon-green/20">
      <div className="flex items-center gap-4">
        <span className="text-neon-green font-bold text-sm tracking-widest font-mono">
          ROG CONTROL
        </span>
        <span className="text-[10px] text-gray-600 font-mono">
          G14 2023
        </span>
      </div>

      <div className="flex items-center gap-3">
        {badges.map((b) => (
          <span
            key={b.label}
            className={`text-[9px] font-mono ${
              b.active ? 'text-neon-green' : 'text-gray-700'
            }`}
          >
            {b.active ? '●' : '○'} {b.label}
          </span>
        ))}
        <div className="w-2 h-2 rounded-full ml-2" style={{
          backgroundColor: connected ? '#00ff00' : '#ff4444',
          boxShadow: connected ? '0 0 6px #00ff00' : '0 0 6px #ff4444',
        }} />
      </div>
    </header>
  );
}