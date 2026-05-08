import { useMemo } from 'react';

interface BarProps {
  value: number;
  max: number;
  label: string;
  showValue?: boolean;
  unit?: string;
  colorFn?: (pct: number) => string;
}

const defaultColor = (pct: number) => {
  if (pct >= 80) return '#ff4444';
  if (pct >= 60) return '#ffaa00';
  if (pct >= 40) return '#ffff00';
  return '#00ff00';
};

export default function ProgressBar({ value, max, label, showValue = true, unit = '', colorFn = defaultColor }: BarProps) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const color = colorFn(pct);

  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-gray-400 w-16 shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-black/40 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${pct}%`,
            backgroundColor: color,
            boxShadow: `0 0 6px ${color}`,
          }}
        />
      </div>
      {showValue && (
        <span className="text-[11px] font-mono w-16 text-right" style={{ color }}>
          {value.toFixed(1)}{unit}
        </span>
      )}
    </div>
  );
}