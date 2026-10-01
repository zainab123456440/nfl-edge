// components/games/BiggestMoves.tsx
"use client";

import { motion } from "framer-motion";
import { TrendingUp, TrendingDown } from "lucide-react";
import type { BiggestMove } from "../../lib/type";
import { cn } from "../../lib/utils";

interface BiggestMovesProps {
  moves: BiggestMove[];
}

export default function BiggestMoves({ moves }: BiggestMovesProps) {
  // Ignore zero / invalid moves so the panel never shows "+0.0" rows
  const real = (moves ?? []).filter(
    (m) => Number.isFinite(m.amount) && Math.abs(m.amount) > 0
  );

  // Nothing to show: render nothing (no empty card)
  if (real.length === 0) return null;

  const maxAmount = Math.max(...real.map((m) => Math.abs(m.amount)), 0.5);

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 h-fit sticky top-20">
      <h3 className="text-sm font-semibold text-[var(--text)] mb-4 flex items-center gap-2">
        <TrendingUp className="h-4 w-4 text-[var(--blue)]" />
        Biggest Moves
      </h3>

      <div className="space-y-3">
        {real.slice(0, 8).map((move, i) => {
          const isUp = move.direction === "up";
          // direction decides the sign, so "down" moves always show a minus
          const signed = isUp ? Math.abs(move.amount) : -Math.abs(move.amount);
          const widthPercent = (Math.abs(move.amount) / maxAmount) * 100;

          return (
            <motion.div
              key={`${move.gameId}-${move.market}-${i}`}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05, duration: 0.35 }}
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="min-w-0 flex-1 truncate text-xs font-medium text-[var(--text)]">
                  {move.matchup}
                </span>
                <div className="flex shrink-0 items-center gap-1">
                  {isUp ? (
                    <TrendingUp className="h-3 w-3 text-[var(--green)]" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-[var(--red)]" />
                  )}
                  <span
                    className={cn(
                      "text-xs font-semibold tabular-nums",
                      isUp ? "text-[var(--green)]" : "text-[var(--red)]"
                    )}
                  >
                    {signed > 0 ? "+" : ""}
                    {signed.toFixed(1)} pts
                  </span>
                </div>
              </div>

              <div className="h-1.5 w-full rounded-full bg-[var(--bg)] overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${widthPercent}%` }}
                  transition={{ delay: i * 0.05 + 0.1, duration: 0.5, ease: "easeOut" }}
                  className={cn(
                    "h-full rounded-full",
                    isUp ? "bg-[var(--green)]" : "bg-[var(--red)]"
                  )}
                />
              </div>

              <div className="mt-0.5 text-[10px] text-[var(--muted)] capitalize">
                {move.market}
                {move.book ? ` · ${move.book}` : ""}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}