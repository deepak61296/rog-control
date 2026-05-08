import { useTelemetry } from '@/hooks/useTelemetry';
import Header from '@/components/Header';
import CpuPanel from '@/components/CpuPanel';
import NvidiaPanel from '@/components/NvidiaPanel';
import AmdGpuPanel from '@/components/AmdGpuPanel';
import CoolingPanel from '@/components/CoolingPanel';
import PowerPanel from '@/components/PowerPanel';
import BatteryPanel from '@/components/BatteryPanel';
import ProfilesPanel from '@/components/ProfilesPanel';
import LogsPanel from '@/components/LogsPanel';

export default function App() {
  useTelemetry();

  return (
    <div className="h-screen flex flex-col bg-cyber-black overflow-hidden">
      <Header />

      <main className="flex-1 p-4 overflow-y-auto" style={{
        background: 'radial-gradient(ellipse at 50% 0%, rgba(0,255,0,0.03) 0%, transparent 60%)',
      }}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Row 1 */}
          <CpuPanel />
          <AmdGpuPanel />
          <NvidiaPanel />

          {/* Row 2 */}
          <CoolingPanel />
          <div className="flex flex-col gap-4">
            <BatteryPanel />
            <ProfilesPanel />
          </div>
          <div className="flex flex-col gap-4">
            <PowerPanel />
            <LogsPanel />
          </div>
        </div>

        <footer className="mt-4 text-center text-[9px] text-gray-700 font-mono">
          Press q/Ctrl+C to quit &middot; ROG Control v1.0
        </footer>
      </main>
    </div>
  );
}