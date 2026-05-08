import { motion } from 'framer-motion';
import GlassPanel from './GlassPanel';
import { useDashboardStore } from '@/store/dashboardStore';

const presets = [
  { name: 'quiet', label: 'Silent', color: '#00ff00', key: 'q' },
  { name: 'cool', label: 'Cool', color: '#00cc88', key: 'c' },
  { name: 'balanced', label: 'Balanced', color: '#00ffff', key: 'b' },
  { name: 'performance', label: 'Performance', color: '#ffaa00', key: 'p' },
  { name: 'max', label: 'Maximum', color: '#ff4444', key: 'm' },
];

export default function ProfilesPanel() {
  const sendCommand = useDashboardStore((s) => s.sendCommand);
  const connected = useDashboardStore((s) => s.backendConnected);

  const applyPreset = async (name: string) => {
    await sendCommand('set_quick_preset', { name });
  };

  return (
    <GlassPanel title="Quick Presets" accent="pink">
      <div className="grid grid-cols-5 gap-2">
        {presets.map((preset) => (
          <motion.button
            key={preset.name}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            disabled={!connected}
            onClick={() => applyPreset(preset.name)}
            className="flex flex-col items-center gap-1 p-2 rounded-lg glass hover:border-opacity-50 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            style={{ borderColor: `${preset.color}33` }}
          >
            <span className="text-[10px] font-mono" style={{ color: preset.color }}>
              [{preset.key}]
            </span>
            <span className="text-[9px] text-gray-400 font-mono text-center leading-tight">
              {preset.label}
            </span>
          </motion.button>
        ))}
      </div>
    </GlassPanel>
  );
}