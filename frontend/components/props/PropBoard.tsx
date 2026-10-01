
"use client";

import type { BoardRow } from "../../types/props";
import { fmtOdds } from "../../lib/propapi";

function HitBar({ row }: { row: BoardRow }) {
  const h = row.hit_rate;

  if (!h || h.over_pct == null) {
    return <span className="text-[var(--muted)]">–</span>;
  }

  const tone =
    h.over_pct >= 60
      ? "bg-emerald-400"
      : h.over_pct <= 40
        ? "bg-rose-400"
        : "bg-amber-400";

  return (
    <div className="w-28">
      <div className="flex justify-between text-xs tabular-nums">
        <span className="text-[var(--text)]">
          {h.over}/{h.games} over
        </span>

        <span className="text-[var(--muted)]">
          {Math.round(h.over_pct)}%
        </span>
      </div>

      <div className="mt-1 h-1.5 rounded-full bg-[var(--border)]">
        <div
          className={`h-1.5 rounded-full ${tone}`}
          style={{ width: `${h.over_pct}%` }}
        />
      </div>
    </div>
  );
}

function MobilePropCard({
  row,
  books,
  onRowClick,
}: {
  row: BoardRow;
  books: [string, string][];
  onRowClick: (r: BoardRow) => void;
}) {
  const lines = row.books
    .map((b) => b.line)
    .filter((l): l is number => l != null);

  const low = lines.length ? Math.min(...lines) : null;

  return (
    <button
      type="button"
      onClick={() => onRowClick(row)}
      className="w-full rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-left transition-colors active:bg-white/[0.05]"
    >
      {/* Player */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-semibold text-[var(--text)]">
            {row.player_name}
          </div>

          <div className="mt-0.5 text-xs text-[var(--muted)]">
            {row.team} {row.position}
          </div>
        </div>

        <span className="shrink-0 rounded-md bg-[var(--accent)]/10 px-2 py-1 text-xs font-medium text-[var(--accent)]">
          View
        </span>
      </div>

      {/* Market */}
      <div className="mt-4">
        <div className="text-xs text-[var(--muted)]">
          Market
        </div>

        <div className="mt-1 text-sm font-medium text-[var(--text)]">
          {row.market_label ?? row.market}
        </div>
      </div>

      {/* Last 10 */}
      <div className="mt-4">
        <div className="mb-2 text-xs text-[var(--muted)]">
          Last 10
        </div>

        <HitBar row={row} />
      </div>

      {/* Sportsbooks */}
      <div className="mt-4 border-t border-[var(--border)] pt-4">
        <div className="mb-3 text-xs font-medium text-[var(--muted)]">
          Sportsbooks
        </div>

        <div className="grid grid-cols-2 gap-2">
          {books.map(([k, name]) => {
            const b = row.books.find((x) => x.key === k);

            if (!b || b.line == null) {
              return (
                <div
                  key={k}
                  className="rounded-lg border border-[var(--border)] p-3"
                >
                  <div className="text-xs text-[var(--muted)]">
                    {name}
                  </div>

                  <div className="mt-1 text-sm text-[var(--muted)]">
                    –
                  </div>
                </div>
              );
            }

            const move = b.line_movement ?? 0;

            return (
              <div
                key={k}
                className="rounded-lg border border-[var(--border)] p-3"
              >
                <div className="truncate text-xs text-[var(--muted)]">
                  {name}
                </div>

                <div
                  className={`mt-1 font-semibold ${
                    b.line === low
                      ? "text-emerald-300"
                      : "text-[var(--text)]"
                  }`}
                >
                  {b.line}
                </div>

                <div className="mt-0.5 text-xs text-[var(--muted)]">
                  O {fmtOdds(b.over_odds)} · U {fmtOdds(b.under_odds)}
                </div>

                {move !== 0 && (
                  <div
                    className={`mt-1 text-xs ${
                      move > 0
                        ? "text-emerald-300"
                        : "text-rose-300"
                    }`}
                  >
                    {move > 0 ? "▲" : "▼"} {Math.abs(move)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </button>
  );
}

export default function PropsBoard({
  rows,
  books,
  onRowClick,
}: {
  rows: BoardRow[];
  books: [string, string][];
  onRowClick: (r: BoardRow) => void;
}) {
  return (
    <>
      {/* Desktop / Tablet table */}
      <div className="hidden overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)] md:block">
        <table className="w-full min-w-[820px] text-sm tabular-nums">
          <thead>
            <tr className="text-left text-xs font-medium text-[var(--muted)]">
              <th className="p-4">Player</th>
              <th className="p-4">Market</th>
              <th className="p-4">Last 10</th>

              {books.map(([k, n]) => (
                <th
                  key={k}
                  className="p-4 text-center"
                >
                  {n}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.map((r) => {
              const lines = r.books
                .map((b) => b.line)
                .filter((l): l is number => l != null);

              const low = lines.length
                ? Math.min(...lines)
                : null;

              return (
                <tr
                  key={`${r.player_id}-${r.market}-${r.game_id}`}
                  onClick={() => onRowClick(r)}
                  className="cursor-pointer border-t border-[var(--border)] hover:bg-white/[0.03]"
                >
                  <td className="p-4">
                    <div className="font-medium text-[var(--text)]">
                      {r.player_name}
                    </div>

                    <div className="text-xs text-[var(--muted)]">
                      {r.team} {r.position}
                    </div>
                  </td>

                  <td className="p-4 text-[var(--muted)]">
                    {r.market_label ?? r.market}
                  </td>

                  <td className="p-4">
                    <HitBar row={r} />
                  </td>

                  {books.map(([k]) => {
                    const b = r.books.find(
                      (x) => x.key === k
                    );

                    if (!b || b.line == null) {
                      return (
                        <td
                          key={k}
                          className="p-4 text-center text-[var(--muted)]"
                        >
                          –
                        </td>
                      );
                    }

                    const move = b.line_movement ?? 0;

                    return (
                      <td
                        key={k}
                        className="p-4 text-center"
                      >
                        <div
                          className={`font-semibold ${
                            b.line === low
                              ? "text-emerald-300"
                              : "text-[var(--text)]"
                          }`}
                        >
                          {b.line}
                        </div>

                        <div className="text-xs text-[var(--muted)]">
                          O {fmtOdds(b.over_odds)} · U{" "}
                          {fmtOdds(b.under_odds)}
                        </div>

                        {move !== 0 && (
                          <div
                            className={`text-xs ${
                              move > 0
                                ? "text-emerald-300"
                                : "text-rose-300"
                            }`}
                          >
                            {move > 0 ? "▲" : "▼"}{" "}
                            {Math.abs(move)}
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="space-y-3 md:hidden">
        {rows.map((row) => (
          <MobilePropCard
            key={`${row.player_id}-${row.market}-${row.game_id}`}
            row={row}
            books={books}
            onRowClick={onRowClick}
          />
        ))}
      </div>
    </>
  );
}
