// components/games/LineMovementChart.tsx

"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts";
import type { LineSeries, Injury } from "../../lib/type";

interface LineMovementChartProps {
  series: LineSeries[];
  open: number;
  injuries?: Injury[];
  market?: "spread" | "total";
}

// Nice colors for different sportsbooks
const BOOK_COLORS: Record<string, string> = {
  draftkings: "#53d337",
  fanduel: "#1493ff",
  betmgm: "#c4a35a",
  caesars: "#f5c518",
  pointsbet: "#e31837",
  default: "#38bdf8",
};

function getBookColor(book: string) {
  return BOOK_COLORS[book.toLowerCase()] ?? BOOK_COLORS.default;
}

export default function LineMovementChart({
  series,
  open,
  injuries = [],
  market = "spread",
}: LineMovementChartProps) {
  if (!series || series.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--bg)] text-sm text-[var(--muted)]">
        No line history available
      </div>
    );
  }

  // Reshape data: collect all unique timestamps and build rows
  const timeSet = new Set<string>();
  series.forEach((s) => s.points.forEach((p) => timeSet.add(p.time)));
  const times = Array.from(timeSet).sort(
    (a, b) => new Date(a).getTime() - new Date(b).getTime()
  );

  const chartData = times.map((time) => {
    const row: Record<string, string | number | null> = {
      time,
      label: new Date(time).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }),
    };

    series.forEach((s) => {
      const point = s.points.find((p) => p.time === time);
      row[s.book] = point ? point.value : null;
    });

    return row;
  });

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          
          <XAxis
            dataKey="label"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={{ stroke: "#334155" }}
            tickLine={false}
            minTickGap={40}
          />
          
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            domain={["auto", "auto"]}
            width={40}
          />

          <Tooltip
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            labelStyle={{ color: "#f1f5f9" }}
          />

          <Legend
            wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }}
          />

          {/* Opening line (dashed) */}
          <ReferenceLine
            y={open}
            stroke="#94a3b8"
            strokeDasharray="4 4"
            label={{
              value: "Open",
              position: "insideTopRight",
              fill: "#94a3b8",
              fontSize: 11,
            }}
          />

          {/* Injury markers (amber vertical lines) */}
          {injuries.map((injury, idx) => {
            const label = new Date(injury.reportedAt).toLocaleString("en-US", {
              month: "short",
              day: "numeric",
              hour: "numeric",
              minute: "2-digit",
            });

            return (
              <ReferenceLine
                key={`injury-${idx}`}
                x={label}
                stroke="#f59e0b"
                strokeDasharray="3 3"
                label={{
                  value: "Injury",
                  position: "top",
                  fill: "#f59e0b",
                  fontSize: 10,
                }}
              />
            );
          })}

          {/* One line per sportsbook */}
          {series.map((s) => (
            <Line
              key={s.book}
              type="stepAfter"          // important: lines jump, they don't slide
              dataKey={s.book}
              name={s.book}
              stroke={getBookColor(s.book)}
              strokeWidth={2}
              dot={false}
              connectNulls
              animationDuration={800}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}