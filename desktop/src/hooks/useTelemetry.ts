import { useEffect } from 'react';
import { useDashboardStore } from '@/store/dashboardStore';

export function useTelemetry() {
  const setTelemetry = useDashboardStore((s) => s.setTelemetry);
  const setBackendStatus = useDashboardStore((s) => s.setBackendStatus);

  useEffect(() => {
    const api = window.rogAPI;
    if (!api) {
      // Browser/dev mode: poll Python server directly
      const ws = new WebSocket('ws://127.0.0.1:9876');

      ws.onopen = () => {
        setBackendStatus({ connected: true });
      };

      ws.onmessage = (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data as string);
          if (data.type === 'telemetry') setTelemetry(data);
        } catch {}
      };

      ws.onclose = () => {
        setBackendStatus({ connected: false });
      };

      return () => {
        ws.close();
      };
    }

    // Electron mode: use IPC
    const onTelemetry = (data: any) => {
      if (data.type === 'telemetry') setTelemetry(data);
    };
    const onStatus = (status: any) => {
      setBackendStatus(status);
    };

    api.onTelemetry(onTelemetry);
    api.onBackendStatus(onStatus);

    api.getBackendStatus().then((connected: boolean) => {
      setBackendStatus({ connected });
    });

    return () => {
      // Cleanup handled by ipcRenderer
    };
  }, []);
}
