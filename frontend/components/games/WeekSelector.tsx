// components/games/WeekSelector.tsx
"use client";

import { cn } from "../../lib/utils";

interface WeekSelectorProps {
  selectedWeek: number;
  currentWeek: number;
  onChange: (week: number) => void;
  totalWeeks?: number;
}

export default function WeekSelector({
  selectedWeek,
  currentWeek,
  onChange,
  totalWeeks = 18,
}: WeekSelectorProps) {
  const weeks = Array.from({ length: totalWeeks }, (_, i) => i + 1);

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
        Week
      </span>
      <div className="flex gap-1.5 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {weeks.map((w) => {
          const isSelected = w === selectedWeek;
          const isCurrent = w === currentWeek;
          const isPast = w < currentWeek;

          return (
            <button
              key={w}
              type="button"
              onClick={() => onChange(w)}
              aria-pressed={isSelected}
              aria-label={`Week ${w}${isCurrent ? " (current)" : ""}`}
              title={isCurrent ? "Current week" : isPast ? "Archived" : "Upcoming"}
              className={cn(
                "relative flex h-9 w-9 shrink-0 items-center justify-center rounded-md border text-sm font-semibold tabular-nums transition-all",
                isSelected
                  ? "border-[var(--blue)] bg-[var(--blue)] text-white shadow-md shadow-[var(--blue)]/30"
                  : isCurrent
                  ? "border-[var(--blue)]/60 bg-[var(--card)] text-[var(--blue)] hover:bg-[var(--blue)]/10"
                  : isPast
                  ? "border-[var(--border)] bg-[var(--card)] text-[var(--muted)]/70 hover:text-[var(--text)] hover:border-[var(--muted)]"
                  : "border-[var(--border)] bg-[var(--card)] text-[var(--muted)] hover:text-[var(--text)] hover:border-[var(--muted)]"
              )}
            >
              {w}
              {isCurrent && !isSelected && (
                <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-[var(--blue)] ring-2 ring-[var(--bg)]" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}