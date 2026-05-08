import { useEffect } from 'react';
import { useDashboardStore } from '@/store/dashboardStore';

export function useTelemetry() {
  const setTelemetry = useDashboardStore((s) => s.setTelemetry);
  const setBackendStatus = useDashboardStore((s) => s.setBackendStatus);

  useEffect(() => {
    const api = window.rogAPI;
    if (!api) {
      // Browser dev mode: poll the Python server directly via WebSocket
      const ws = new WebSocket('ws://127.0.0.1:9876');
      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === 'telemetry') setTelemetry(data);
        } catch {}
      };
      ws.onopen = () => setBackendStatus({ connected: true });
      ws.onclose = () => setBackendStatus({ connected: false });
      return () => ws.close();
    }

    api.onTelemetry((data) => {
      if (data.type === 'telemetry') setTelemetry(data);
    });

    api.onBackendStatus((status) => {
      setBackendStatus(status);
    });

    api.getBackendStatus().then((connected) => {
      setBackendStatus({ connected });
    });
  }, []);
}