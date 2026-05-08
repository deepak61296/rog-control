import { useEffect, useRef } from 'react';
import GlassPanel from './GlassPanel';
import { useDashboardStore } from '@/store/dashboardStore';

export default function LogsPanel() {
  const telemetry = useDashboardStore((s) => s.telemetry);
  const lastError = useDashboardStore((s) => s.lastError);
  const connected = useDashboardStore((s) => s.backendConnected);
  const scrollRef = useRef<HTMLDivElement>(null);
  const logsRef = useRef<string[]>([]);

  // Build logs from current state
  const logs: { text: string; color: string }[] = [];

  if (!connected) {
    logs.unshift({ text: 'Backend disconnected', color: '#ff4444' });
  }

  if (lastError) {
    logs.unshift({ text: lastError, color: '#ffff00' });
  }

  if (telemetry) {
    const caps = telemetry.capabilities;
    if (caps?.nvidia && !caps.nvidia.available && caps.nvidia.reason) {
      logs.push({ text: `NVIDIA: ${caps.nvidia.reason}`, color: '#ffff00' });
    }
    if (telemetry.errors.length > 0) {
      for (const err of telemetry.errors.slice(0, 3)) {
        if (err && err !== lastError) {
          logs.push({ text: err, color: '#ff8800' });
        }
      }
    }
  }

  if (logs.length === 0) {
    logs.push({ text: 'All systems nominal', color: '#00ff00' });
  }

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <GlassPanel title="Live Log" accent="cyan">
      <div
        ref={scrollRef}
        className="h-24 overflow-y-auto font-mono text-[10px] space-y-0.5"
      >
        {logs.map((log, i) => (
          <div key={i} style={{ color: log.color }}>
            <span className="text-gray-600 mr-1">&gt;</span>
            {log.text}
          </div>
        ))}
      </div>
    </GlassPanel>
  );
}