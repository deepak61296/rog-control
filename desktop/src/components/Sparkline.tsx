import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';

interface SparklineProps {
  data: { time: number; value: number }[];
  color?: string;
  height?: number;
}

export default function Sparkline({ data, color = '#00ff00', height = 40 }: SparklineProps) {
  if (data.length < 2) {
    return <div className="text-[10px] text-gray-600" style={{ height }}>collecting data...</div>;
  }

  const gradientId = `grad-${color.replace('#', '')}`;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.4} />
            <stop offset="100%" stopColor={color} stopOpacity={0.0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="time" hide />
        <YAxis hide domain={['dataMin', 'dataMax']} />
        <Tooltip
          contentStyle={{
            background: 'rgba(0,10,5,0.9)',
            border: '1px solid rgba(0,255,0,0.3)',
            borderRadius: '8px',
            fontSize: '10px',
            fontFamily: 'JetBrains Mono, monospace',
          }}
          labelStyle={{ color: '#00ff88' }}
          formatter={(value: number) => [`${value.toFixed(1)}°C`, 'Temp']}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#${gradientId})`}
          isAnimationActive={false}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
