// components/props/PropDetailPanel.tsx
"use client";

import { useMemo } from "react";
import type { BoardRow } from "../../types/props";
import { fmtOdds } from "../../lib/propapi";

// American odds -> implied probability (0..1)
const implied = (odds?: number | null) => {
  if (odds == null) return null;
  return odds < 0 ? -odds / (-odds + 100) : 100 / (odds + 100);
};

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
    <h3 className="mb-3 text-sm font-medium text-[var(--text)]">{title}</h3>
    {children}
  </section>
);

const Stat = ({ label, value, sub }: { label: string; value: string; sub?: string }) => (
  <div className="rounded-lg border border-[var(--border)] p-3">
    <p className="text-xs text-[var(--muted)]">{label}</p>
    <p className="mt-1 text-lg font-semibold tabular-nums text-[var(--text)]">{value}</p>
    {sub && <p className="text-xs text-[var(--muted)]">{sub}</p>}
  </div>
);

export default function PropDetailPanel({
  row, open, onClose,
}: { row: BoardRow | null; open: boolean; onClose: () => void }) {
  const summary = useMemo(() => {
    if (!row) return null;
    const books = row.books ?? [];
    const lines = books.map((b) => b.line).filter((l): l is number => l != null);

    const withOver = books.filter((b) => b.over_odds != null);
    const withUnder = books.filter((b) => b.under_odds != null);
    const bestOver = withOver.length
      ? withOver.reduce((a, b) => (b.over_odds! > a.over_odds! ? b : a))
      : null;
    const bestUnder = withUnder.length
      ? withUnder.reduce((a, b) => (b.under_odds! > a.under_odds! ? b : a))
      : null;

    // Lowest line is the best number for Over, highest for Under
    const lowLine = lines.length ? Math.min(...lines) : null;
    const highLine = lines.length ? Math.max(...lines) : null;

    // Average no-vig Over probability across books that post both prices
    const probs = books
      .map((b) => {
        const o = implied(b.over_odds);
        const u = implied(b.under_odds);
        return o != null && u != null ? o / (o + u) : null;
      })
      .filter((p): p is number => p != null);
    const overProb = probs.length ? probs.reduce((a, b) => a + b, 0) / probs.length : null;

    const avgLine = lines.length ? lines.reduce((a, b) => a + b, 0) / lines.length : null;

    return { bookCount: books.length, lowLine, highLine, avgLine, bestOver, bestUnder, overProb };
  }, [row]);

  const line = row?.consensus_line ?? summary?.avgLine ?? null;

  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 z-30 bg-black/50 transition-opacity ${open ? "opacity-100" : "pointer-events-none opacity-0"}`}
      />
      <aside
        className={`fixed inset-y-0 right-0 z-40 w-full max-w-xl space-y-4 overflow-y-auto border-l border-[var(--border)] bg-[var(--bg,#0f1b2d)] p-6 transition-transform duration-300 ${open ? "translate-x-0" : "translate-x-full"}`}
      >
        {row && summary && (
          <>
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold text-[var(--text)]">{row.player_name}</h2>
                <p className="text-sm text-[var(--muted)]">
                  {row.market_label ?? row.market} · {row.team} {row.position}
                </p>
              </div>
              <button onClick={onClose} className="rounded-md px-2 py-1 text-[var(--muted)] hover:text-[var(--text)]">
                Close
              </button>
            </div>

            <Section title="Prop at a glance">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <Stat
                  label="Consensus line"
                  value={line != null ? String(Number(line.toFixed(1))) : "–"}
                  sub={`${summary.bookCount} sportsbook${summary.bookCount === 1 ? "" : "s"}`}
                />
                <Stat
                  label="Line range"
                  value={
                    summary.lowLine != null
                      ? summary.lowLine === summary.highLine
                        ? String(summary.lowLine)
                        : `${summary.lowLine} – ${summary.highLine}`
                      : "–"
                  }
                  sub={
                    summary.lowLine != null && summary.highLine != null && summary.highLine > summary.lowLine
                      ? `${(summary.highLine - summary.lowLine).toFixed(1)} pt spread between books`
                      : "Books agree"
                  }
                />
                <Stat
                  label="Market leans Over"
                  value={summary.overProb != null ? `${Math.round(summary.overProb * 100)}%` : "–"}
                  sub={summary.overProb != null ? `Under ${Math.round((1 - summary.overProb) * 100)}% · vig removed` : undefined}
                />
                <Stat
                  label="Best Over price"
                  value={summary.bestOver ? fmtOdds(summary.bestOver.over_odds) : "–"}
                  sub={summary.bestOver ? summary.bestOver.name ?? summary.bestOver.key : undefined}
                />
                <Stat
                  label="Best Under price"
                  value={summary.bestUnder ? fmtOdds(summary.bestUnder.under_odds) : "–"}
                  sub={summary.bestUnder ? summary.bestUnder.name ?? summary.bestUnder.key : undefined}
                />
                <Stat
                  label="Best line"
                  value={
                    summary.lowLine != null && summary.highLine != null && summary.highLine > summary.lowLine
                      ? `O ${summary.lowLine} / U ${summary.highLine}`
                      : "–"
                  }
                  sub="Lowest for Over, highest for Under"
                />
              </div>
            </Section>

            <Section title="Sportsbooks now">
              <div className="divide-y divide-[var(--border)] text-sm tabular-nums">
                {row.books.map((b) => {
                  const isBestOver = summary.bestOver?.key === b.key;
                  const isBestUnder = summary.bestUnder?.key === b.key;
                  return (
                    <div key={b.key} className="flex items-center justify-between py-2">
                      <span className="text-[var(--text)]">{b.name ?? b.key}</span>
                      <span className="text-[var(--muted)]">
                        {b.line ?? "–"} ·{" "}
                        <span className={isBestOver ? "font-semibold text-emerald-400" : ""}>O {fmtOdds(b.over_odds)}</span>
                        {" · "}
                        <span className={isBestUnder ? "font-semibold text-rose-400" : ""}>U {fmtOdds(b.under_odds)}</span>
                      </span>
                    </div>
                  );
                })}
              </div>
              <p className="mt-2 text-xs text-[var(--muted)]">
                Green and red mark the best Over and Under prices.
              </p>
            </Section>
          </>
        )}
      </aside>
    </>
  );
}