import { useMemo } from 'react';

interface GaugeProps {
  value: number;
  max: number;
  size?: number;
  strokeWidth?: number;
  label: string;
  unit: string;
  colorFn?: (pct: number) => string;
}

const defaultColor = (pct: number) => {
  if (pct >= 80) return '#ff4444';
  if (pct >= 60) return '#ffaa00';
  if (pct >= 40) return '#ffff00';
  return '#00ff00';
};

export default function Gauge({
  value,
  max,
  size = 90,
  strokeWidth = 6,
  label,
  unit,
  colorFn = defaultColor,
}: GaugeProps) {
  const pct = useMemo(() => max > 0 ? Math.min(100, (value / max) * 100) : 0, [value, max]);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;
  const color = colorFn(pct);
  const center = size / 2;

  return (
    <div className="flex flex-col items-center relative">
      <svg width={size} height={size}>
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="rgba(0,255,0,0.08)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${center} ${center})`}
          style={{
            transition: 'stroke-dashoffset 0.6s ease, stroke 0.6s ease',
            filter: `drop-shadow(0 0 4px ${color})`,
          }}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-sm font-bold font-mono" style={{ color }}>
          {value.toFixed(1)}
        </span>
        <span className="text-[10px] text-gray-500">{unit}</span>
      </div>
      <span className="text-[10px] text-gray-400 mt-1">{label}</span>
    </div>
  );
}
