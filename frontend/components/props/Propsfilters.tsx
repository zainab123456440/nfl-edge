
"use client";

import { useEffect, useState } from "react";
import type { Market } from "../../types/props";

const MAIN_BOOKS: [string, string][] = [
  ["draftkings", "DraftKings"],
  ["fanduel", "FanDuel"],
  ["betmgm", "BetMGM"],
  ["caesars", "Caesars"],
];

type Filters = {
  market: string;
  book: string;
  search: string;
};

export default function PropsFilters({
  markets,
  filters,
  onChange,
}: {
  markets: Market[];
  filters: Filters;
  books?: [string, string][];
  onChange: (key: string, value: string) => void;
}) {
  const [q, setQ] = useState(filters.search);

  // Debounce search so we don't hit the API on every keystroke
  useEffect(() => {
    if (q === filters.search) return;

    const t = setTimeout(() => onChange("search", q), 300);

    return () => clearTimeout(t);
  }, [q]); // eslint-disable-line react-hooks/exhaustive-deps

  const chip = (on: boolean) =>
    `shrink-0 whitespace-nowrap rounded-lg border px-3.5 py-2 text-sm transition ${
      on
        ? "border-[var(--blue)]/50 bg-[var(--blue)]/15 text-[var(--blue)] font-medium"
        : "border-[var(--border)] bg-[var(--card)] text-[var(--muted)] hover:text-[var(--text)]"
    }`;

  return (
    <div className="space-y-4">
      {/* Markets */}
      <div>
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Markets
        </div>

        <div className="-mx-1 overflow-x-auto px-1 pb-1 scrollbar-none">
          <div className="flex min-w-max gap-2">
            <button
              type="button"
              className={chip(!filters.market)}
              onClick={() => onChange("market", "")}
            >
              All markets
            </button>

            {markets.map((m) => (
              <button
                type="button"
                key={m.key}
                className={chip(filters.market === m.key)}
                onClick={() => onChange("market", m.key)}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Search + Sportsbook */}
      <div className="grid grid-cols-1 gap-3 sm:flex sm:flex-wrap sm:items-center">
        {/* Player Search */}
        <div className="w-full sm:w-64">
          <label
            htmlFor="player-search"
            className="mb-1.5 block text-xs font-medium text-[var(--muted)]"
          >
            Player
          </label>

          <input
            id="player-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search player"
            className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 text-sm text-[var(--text)] outline-none placeholder:text-[var(--muted)] focus:border-[var(--blue)]"
          />
        </div>

        {/* Sportsbook Filter */}
        <div className="w-full sm:w-56">
          <label
            htmlFor="sportsbook-filter"
            className="mb-1.5 block text-xs font-medium text-[var(--muted)]"
          >
            Sportsbook
          </label>

          <select
            id="sportsbook-filter"
            value={filters.book}
            onChange={(e) => onChange("book", e.target.value)}
            className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 text-sm text-[var(--text)] outline-none focus:border-[var(--blue)]"
          >
            <option value="">All sportsbooks</option>

            {MAIN_BOOKS.map(([key, name]) => (
              <option key={key} value={key}>
                {name}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}