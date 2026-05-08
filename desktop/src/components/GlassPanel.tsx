import { motion } from 'framer-motion';
import type { ReactNode } from 'react';

interface GlassPanelProps {
  title: string;
  accent?: 'green' | 'cyan' | 'pink' | 'orange' | 'teal';
  children: ReactNode;
  className?: string;
  statusBadge?: { label: string; active: boolean } | null;
}

const accentColors = {
  green: { border: 'border-neon-green/30', glow: 'glow-green', text: 'text-neon-green' },
  cyan: { border: 'border-neon-cyan/30', glow: 'glow-cyan', text: 'text-neon-cyan' },
  pink: { border: 'border-neon-pink/30', glow: 'glow-pink', text: 'text-neon-pink' },
  orange: { border: 'border-neon-orange/30', glow: 'shadow-[0_0_15px_rgba(255,102,0,0.1)]', text: 'text-neon-orange' },
  teal: { border: 'border-neon-teal/30', glow: 'shadow-[0_0_15px_rgba(0,204,136,0.1)]', text: 'text-neon-teal' },
};

export default function GlassPanel({ title, accent = 'green', children, className = '', statusBadge }: GlassPanelProps) {
  const colors = accentColors[accent];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className={`glass rounded-xl p-4 ${colors.glow} ${className}`}
    >
      <div className={`flex items-center justify-between mb-3 pb-2 border-b ${colors.border}`}>
        <h3 className={`text-xs font-semibold uppercase tracking-wider ${colors.text}`}>
          {title}
        </h3>
        {statusBadge && (
          <span className={`text-[10px] ${statusBadge.active ? 'text-neon-green' : 'text-gray-600'}`}>
            {statusBadge.active ? '●' : '○'} {statusBadge.label}
          </span>
        )}
      </div>
      <div className="space-y-2">
        {children}
      </div>
    </motion.div>
  );
}