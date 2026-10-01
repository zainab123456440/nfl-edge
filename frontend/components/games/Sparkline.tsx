// components/games/Sparkline.tsx

"use client";

import { LineChart, Line, ResponsiveContainer } from "recharts";

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

export default function Sparkline({
  data,
  width = 64,
  height = 22,
  color = "#38bdf8",
}: SparklineProps) {
  if (!data || data.length < 2) {
    return (
      <div
        style={{ width, height }}
        className="flex items-center justify-center text-[10px] text-[var(--muted)]"
      >
        —
      </div>
    );
  }

  // Convert plain number[] into the shape Recharts expects
  const chartData = data.map((value, index) => ({ index, value }));

  // Decide color based on overall direction
  const first = data[0];
  const last = data[data.length - 1];
  const strokeColor = last > first ? "#22c55e" : last < first ? "#ef4444" : color;

  return (
    <div style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line
            type="monotone"
            dataKey="value"
            stroke={strokeColor}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}