// components/games/FilterBar.tsx
"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import { Search } from "lucide-react";
import { cn } from "../../lib/utils";
import { getCurrentWeek } from "../../lib/time";

const WEEKS = Array.from({ length: 18 }, (_, i) => i + 1);

const BOOKS = [
  { value: "", label: "All Books" },
  { value: "draftkings", label: "DraftKings" },
  { value: "fanduel", label: "FanDuel" },
  { value: "betmgm", label: "BetMGM" },
  { value: "caesars", label: "Caesars" },
];

/*
 * Quick team suggestions.
 * The search box still allows users to search for ANY NFL team.
 */
const QUICK_TEAMS = [
  "Chiefs",
  "Eagles",
  "Ravens",
  "Bills",
  "Cowboys",
  "49ers",
  "Lions",
  "Packers",
  "Bengals",
];

export default function FilterBar() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const currentWeek = useMemo(() => getCurrentWeek(), []);
  const urlWeek = searchParams.get("week");
  const selectedWeek = urlWeek ? Number(urlWeek) : currentWeek;
  const currentBook = searchParams.get("book") ?? "";
  const currentTeam = searchParams.get("team") ?? "";

  const [teamInput, setTeamInput] = useState(currentTeam);

  const updateParams = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());

      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }

      startTransition(() => {
        router.replace(`${pathname}?${params.toString()}`, { scroll: false });
      });
    },
    [pathname, router, searchParams]
  );

  useEffect(() => {
    if (teamInput === currentTeam) return;

    const t = setTimeout(() => {
      updateParams("team", teamInput.trim());
    }, 300);

    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teamInput]);

  const handleQuickTeam = (team: string) => {
    setTeamInput(team);
    updateParams("team", team);
  };

  return (
    <div
      className={cn(
        "space-y-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-3 sm:p-4",
        isPending && "opacity-70"
      )}
    >
      {/* Week selector: square boxes */}
      <div className="flex items-center gap-3">
        <span className="shrink-0 text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
          Week
        </span>

        <div className="flex gap-1.5 overflow-x-auto py-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {WEEKS.map((w) => {
            const isSelected = w === selectedWeek;
            const isCurrent = w === currentWeek;
            const isPast = w < currentWeek;

            return (
              <button
                key={w}
                type="button"
                onClick={() => updateParams("week", String(w))}
                aria-pressed={isSelected}
                title={
                  isCurrent
                    ? "Current week"
                    : isPast
                    ? "Archived"
                    : "Upcoming"
                }
                className={cn(
                  "relative flex h-9 w-9 shrink-0 items-center justify-center rounded-md border text-sm font-semibold tabular-nums transition-all",
                  isSelected
                    ? "border-[var(--blue)] bg-[var(--blue)] text-slate-900 shadow-md"
                    : isCurrent
                    ? "border-[var(--blue)] bg-[var(--bg)] text-[var(--blue)] hover:bg-[var(--blue)]/10"
                    : isPast
                    ? "border-[var(--border)] bg-[var(--bg)] text-[var(--muted)]/70 hover:text-[var(--text)]"
                    : "border-[var(--border)] bg-[var(--bg)] text-[var(--muted)] hover:text-[var(--text)]"
                )}
              >
                {w}

                {isCurrent && !isSelected && (
                  <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-[var(--blue)] ring-2 ring-[var(--card)]" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="h-px w-full bg-[var(--border)]" />

      {/* Book + Team search */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:gap-4">
        {/* Book */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="book"
            className="shrink-0 text-xs font-medium text-[var(--muted)]"
          >
            Book
          </label>

          <select
            id="book"
            value={currentBook}
            onChange={(e) => updateParams("book", e.target.value)}
            className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-1.5 text-sm text-[var(--text)] outline-none focus:ring-2 focus:ring-[var(--blue)]/50"
          >
            {BOOKS.map((b) => (
              <option key={b.value} value={b.value}>
                {b.label}
              </option>
            ))}
          </select>
        </div>

        {/* Team search + quick teams */}
        <div className="min-w-[160px] flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted)]" />

            <input
              type="text"
              placeholder="Search team..."
              value={teamInput}
              onChange={(e) => setTeamInput(e.target.value)}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] py-1.5 pl-9 pr-3 text-sm text-[var(--text)] placeholder:text-[var(--muted)] outline-none focus:ring-2 focus:ring-[var(--blue)]/50"
            />
          </div>

          {/* Quick team suggestions */}
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-[11px] font-medium uppercase tracking-wide text-[var(--muted)]">
              Quick:
            </span>

            {QUICK_TEAMS.map((team) => {
              const isSelected =
                currentTeam.toLowerCase() === team.toLowerCase();

              return (
                <button
                  key={team}
                  type="button"
                  onClick={() => handleQuickTeam(team)}
                  className={cn(
                    "rounded-md border px-2.5 py-1 text-xs font-medium transition-colors",
                    isSelected
                      ? "border-[var(--blue)] bg-[var(--blue)]/15 text-[var(--blue)]"
                      : "border-[var(--border)] bg-[var(--bg)] text-[var(--muted)] hover:border-[var(--blue)]/50 hover:text-[var(--text)]"
                  )}
                >
                  {team}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}