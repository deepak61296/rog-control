import GlassPanel from './GlassPanel';
import Gauge from './Gauge';
import { useDashboardStore } from '@/store/dashboardStore';

export default function CoolingPanel() {
  const telemetry = useDashboardStore((s) => s.telemetry);
  const cooling = telemetry?.cooling;
  const profile = telemetry?.fan_profile;
  const curveEnabled = telemetry?.custom_curve_enabled;

  return (
    <GlassPanel title="Cooling" accent="green">
      <div className="flex items-start justify-around">
        <Gauge
          value={cooling?.cpu_fan_rpm ?? 0}
          max={7000}
          size={80}
          label="CPU Fan"
          unit="RPM"
        />
        <Gauge
          value={cooling?.gpu_fan_rpm ?? 0}
          max={7000}
          size={80}
          label="GPU Fan"
          unit="RPM"
        />
      </div>

      <div className="grid grid-cols-2 gap-1 mt-2">
        <div className="text-[10px] text-gray-500">Profile</div>
        <div className="text-[11px] font-mono text-neon-green text-right">
          {profile ?? '---'}
        </div>
        <div className="text-[10px] text-gray-500">Curve</div>
        <div className="text-[11px] font-mono text-right" style={{
          color: curveEnabled ? '#00ff00' : '#ffff00',
        }}>
          {curveEnabled != null ? (curveEnabled ? 'Custom' : 'Firmware') : '---'}
        </div>
        {telemetry?.nvme_temp_c != null && (
          <>
            <div className="text-[10px] text-gray-500">NVMe</div>
            <div className="text-[11px] font-mono text-neon-green text-right">
              {telemetry.nvme_temp_c.toFixed(1)}°C
            </div>
          </>
        )}
      </div>
    </GlassPanel>
  );
}