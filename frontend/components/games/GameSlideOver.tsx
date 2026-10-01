// components/games/GameSlideOver.tsx
"use client";

import { useState } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { X, Activity, AlertTriangle } from "lucide-react";
import type { Game, LineHistoryResponse } from "../../lib/type";
import { getLineHistory } from "../../lib/api";
import { formatOdds, cn } from "../../lib/utils";
import { formatKickoffFull } from "../../lib/time";
import LineMovementChart from "./LineMovementChart";

interface GameSlideOverProps {
  game: Game | null;
  open: boolean;
  onClose: () => void;
}

export default function GameSlideOver({ game, open, onClose }: GameSlideOverProps) {
  const [market, setMarket] = useState<"spread" | "total">("spread");

  const { data, error, isLoading } = useSWR<LineHistoryResponse>(
    game && open ? `line-history-${game.id}-${market}` : null,
    () => getLineHistory(game!.id, market, game!),
    { revalidateOnFocus: false }
  );

  const showScore = game && game.status !== "scheduled" && game.score;
  const hasHistory = !!data && data.series.length > 1;

  // Only show detail fields that have a value
  const details: [string, string][] = game
    ? ([
        ["Kickoff", formatKickoffFull(game.kickoff)],
        ["Week", `Week ${game.week} · ${game.season}`],
        ["Status", game.status.toUpperCase()],
        game.venue ? ["Venue", game.venue] : null,
      ].filter(Boolean) as [string, string][])
    : [];

  return (
    <AnimatePresence>
      {open && game && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />

          {/* Panel */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 300 }}
            className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-[var(--card)] border-l border-[var(--border)] shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-[var(--text)]">
                    {game.away.abbreviation} @ {game.home.abbreviation}
                  </h2>
                  {game.status === "live" && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-red-500/15 px-2 py-0.5 text-xs font-medium text-red-400">
                      <span className="live-dot" />
                      LIVE
                    </span>
                  )}
                </div>
                <p className="text-sm text-[var(--muted)] mt-0.5">
                  {game.away.name} at {game.home.name}
                  {showScore && (
                    <span className="ml-2 font-medium text-[var(--text)]">
                      {game.score!.away} – {game.score!.home}
                    </span>
                  )}
                </p>
              </div>

              <button
                onClick={onClose}
                aria-label="Close"
                className="rounded-lg p-2 text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--bg)] transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Game details (US Eastern) */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 px-5 py-3 border-b border-[var(--border)]">
              {details.map(([label, value]) => (
                <div key={label}>
                  <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
                    {label}
                  </div>
                  <div className="text-sm text-[var(--text)]">{value}</div>
                </div>
              ))}
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {/* Line Movement */}
              <div>
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-[var(--text)] flex items-center gap-2">
                    <Activity className="h-4 w-4 text-[var(--blue)]" />
                    Line Movement
                  </h3>

                  {/* Market toggle only when there is a chart to switch */}
                  {(hasHistory || isLoading) && (
                    <div className="flex gap-1.5">
                      {(["spread", "total"] as const).map((m) => (
                        <button
                          key={m}
                          onClick={() => setMarket(m)}
                          className={cn(
                            "rounded-md px-3 py-1 text-xs font-medium capitalize transition-colors",
                            market === m
                              ? "bg-[var(--blue)] text-slate-900"
                              : "bg-[var(--bg)] text-[var(--muted)] hover:text-[var(--text)]"
                          )}
                        >
                          {m}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {isLoading ? (
                  <div className="h-72 rounded-lg skeleton" />
                ) : hasHistory ? (
                  <LineMovementChart
                    series={data!.series}
                    open={data!.open}
                    injuries={data!.injuries}
                    market={market}
                  />
                ) : (
                  // Compact note instead of a big empty box
                  <div className="rounded-lg border border-dashed border-[var(--border)] px-4 py-3 text-sm text-[var(--muted)]">
                    {error
                      ? "Couldn't load line history."
                      : "No line movement yet. The chart appears once the lines change."}
                  </div>
                )}
              </div>

              {/* Odds by Book */}
              {game.odds && game.odds.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-[var(--text)] mb-3">
                    Odds by Book
                  </h3>
                  <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-[var(--bg)] text-[var(--muted)] text-left">
                          <th className="px-3 py-2 font-medium">Book</th>
                          <th className="px-3 py-2 font-medium text-right">Spread</th>
                          <th className="px-3 py-2 font-medium text-right">Total</th>
                          <th className="px-3 py-2 font-medium text-right">ML Home</th>
                          <th className="px-3 py-2 font-medium text-right">ML Away</th>
                        </tr>
                      </thead>
                      <tbody>
                        {game.odds.map((o: NonNullable<Game["odds"]>[number]) => (
                          <tr
                            key={o.book}
                            className="border-t border-[var(--border)] hover:bg-[var(--bg)]/50"
                          >
                            <td className="px-3 py-2 capitalize font-medium">{o.book}</td>
                            <td className="px-3 py-2 text-right tabular-nums">
                              {o.spread != null ? (
                                <>
                                  {o.spread > 0 ? "+" : ""}
                                  {o.spread}{" "}
                                  {o.spreadPrice != null && (
                                    <span className="text-[var(--muted)]">
                                      ({formatOdds(o.spreadPrice)})
                                    </span>
                                  )}
                                </>
                              ) : (
                                "—"
                              )}
                            </td>
                            <td className="px-3 py-2 text-right tabular-nums">
                              {o.total != null ? o.total : "—"}
                            </td>
                            <td className="px-3 py-2 text-right tabular-nums">
                              {formatOdds(o.moneylineHome)}
                            </td>
                            <td className="px-3 py-2 text-right tabular-nums">
                              {formatOdds(o.moneylineAway)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Injuries */}
              {data?.injuries && data.injuries.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-[var(--text)] mb-3 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-[var(--amber)]" />
                    Injuries
                  </h3>
                  <div className="space-y-2">
                    {data.injuries.map(
                      (inj: LineHistoryResponse["injuries"][number], i: number) => (
                        <div
                          key={i}
                          className="flex items-start gap-3 rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3"
                        >
                          <div className="mt-0.5 h-2 w-2 rounded-full bg-[var(--amber)] shrink-0" />
                          <div>
                            <div className="text-sm font-medium text-[var(--text)]">
                              {inj.player}{" "}
                              <span className="text-[var(--muted)] font-normal">
                                ({inj.team})
                              </span>
                            </div>
                            <div className="text-xs text-[var(--amber)] mt-0.5">
                              {inj.status}
                            </div>
                            {inj.description && (
                              <p className="text-xs text-[var(--muted)] mt-1">
                                {inj.description}
                              </p>
                            )}
                          </div>
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}