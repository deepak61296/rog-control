import { AreaChart, Area, ResponsiveContainer } from 'recharts';

interface SparklineProps {
  data: { time: number; value: number }[];
  color?: string;
  height?: number;
}

export default function Sparkline({ data, color = '#00ff00', height = 40 }: SparklineProps) {
  if (data.length < 2) {
    return <div className="text-[10px] text-gray-600" style={{ height }}>collecting data...</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`grad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0.0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#grad-${color.replace('#', '')})`}
          isAnimationActive={false}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}