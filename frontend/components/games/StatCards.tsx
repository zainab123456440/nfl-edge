// components/games/StatCards.tsx

"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, Radio, TrendingUp, BarChart3 } from "lucide-react";

interface StatCardsProps {
  gamesThisWeek: number;
  liveNow: number;
  biggestMove: number;
  averageTotal: number;
}

function CountUp({ value, decimals = 0 }: { value: number; decimals?: number }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    let start = 0;
    const end = value;
    const duration = 900;
    const startTime = performance.now();

    const tick = (now: number) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      setDisplay(start + (end - start) * eased);
      if (progress < 1) requestAnimationFrame(tick);
    };

    requestAnimationFrame(tick);
  }, [value]);

  return (
    <span className="tabular-nums">
      {decimals > 0 ? display.toFixed(decimals) : Math.round(display)}
    </span>
  );
}

const cards = [
  {
    key: "gamesThisWeek",
    label: "Games this week",
    icon: Activity,
    color: "text-[var(--blue)]",
    bg: "bg-sky-500/10",
  },
  {
    key: "liveNow",
    label: "Live now",
    icon: Radio,
    color: "text-[var(--red)]",
    bg: "bg-red-500/10",
  },
  {
    key: "biggestMove",
    label: "Biggest move",
    icon: TrendingUp,
    color: "text-[var(--green)]",
    bg: "bg-green-500/10",
  },
  {
    key: "averageTotal",
    label: "Average total",
    icon: BarChart3,
    color: "text-[var(--amber)]",
    bg: "bg-amber-500/10",
  },
] as const;

export default function StatCards({
  gamesThisWeek,
  liveNow,
  biggestMove,
  averageTotal,
}: StatCardsProps) {
  const values = {
    gamesThisWeek,
    liveNow,
    biggestMove,
    averageTotal,
  };

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      {cards.map((card, i) => {
        const Icon = card.icon;
        const value = values[card.key];
        const isDecimal = card.key === "biggestMove" || card.key === "averageTotal";

        return (
          <motion.div
            key={card.key}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08, duration: 0.4, ease: "easeOut" }}
            className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 sm:p-5"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs sm:text-sm font-medium text-[var(--muted)]">
                {card.label}
              </span>
              <div className={`rounded-lg p-1.5 ${card.bg}`}>
                <Icon className={`h-4 w-4 ${card.color}`} />
              </div>
            </div>

            <div className={`text-2xl sm:text-3xl font-semibold tracking-tight ${card.color}`}>
              {card.key === "biggestMove" && value > 0 && (
                <span className="text-lg mr-0.5">+</span>
              )}
              <CountUp value={value} decimals={isDecimal ? 1 : 0} />
              {card.key === "biggestMove" && (
                <span className="text-base font-normal text-[var(--muted)] ml-1">pts</span>
              )}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}