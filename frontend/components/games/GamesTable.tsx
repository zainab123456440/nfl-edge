// components/games/GamesTable.tsx
"use client";

import { motion } from "framer-motion";
import type { Game } from "../../lib/type";
import { formatOdds, formatMove, cn } from "../../lib/utils";
import { formatKickoff } from "../../lib/time";
import Sparkline from "./Sparkline";
import OddsFlashCell from "./OddsFlashCell";

interface GamesTableProps {
  games: Game[];
  onRowClick: (game: Game) => void;
}

const roundHalf = (n: number) => Math.round(n * 2) / 2;

function fmtSpread(v: number | null | undefined) {
  if (v == null) return "—";
  const r = roundHalf(v);
  return `${r > 0 ? "+" : ""}${r}`;
}

function fmtTotal(v: number | null | undefined) {
  return v == null ? "—" : String(roundHalf(v));
}

function StatusBadge({ status }: { status: Game["status"] }) {
  if (status === "live")
    return (
      <span className="inline-flex items-center gap-1 rounded bg-red-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-red-400">
        <span className="live-dot !w-1.5 !h-1.5" />
        LIVE
      </span>
    );
  if (status === "final")
    return (
      <span className="rounded bg-slate-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-[var(--muted)]">
        FINAL
      </span>
    );
  return (
    <span className="rounded bg-blue-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-[var(--blue)]">
      SCHEDULED
    </span>
  );
}

export default function GamesTable({ games, onRowClick }: GamesTableProps) {
  if (!games || games.length === 0) {
    return (
      <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-12 text-center">
        <p className="text-[var(--muted)]">No games found for the selected filters.</p>
      </div>
    );
  }

  // Only show columns that have real data this week
  const hasMove = games.some((g) => !!g.spreadMove);
  const hasTrend = games.some((g) => (g.sparkline?.length ?? 0) > 1);
  const hasVenue = games.some((g) => !!g.venue);

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--bg)]/60 text-[var(--muted)] text-left">
              <th className="px-4 py-3 font-medium min-w-[200px]">Matchup</th>
              <th className="px-4 py-3 font-medium">Kickoff</th>
              <th className="px-4 py-3 font-medium">Status</th>
              {hasVenue && (
                <th className="px-4 py-3 font-medium hidden lg:table-cell">Venue</th>
              )}
              <th className="px-4 py-3 font-medium text-right">Spread (Home)</th>
              <th className="px-4 py-3 font-medium text-right">Total</th>
              <th className="px-4 py-3 font-medium text-right">ML Home</th>
              <th className="px-4 py-3 font-medium text-right">ML Away</th>
              {hasMove && <th className="px-4 py-3 font-medium text-center">Move</th>}
              {hasTrend && (
                <th className="px-4 py-3 font-medium text-center w-[80px]">Trend</th>
              )}
            </tr>
          </thead>

          <tbody>
            {games.map((game, i) => {
              const isLive = game.status === "live";
              const showScore = game.status !== "scheduled" && game.score;

              return (
                <motion.tr
                  key={game.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04, duration: 0.3 }}
                  onClick={() => onRowClick(game)}
                  className={cn(
                    "border-b border-[var(--border)] cursor-pointer transition-colors",
                    "hover:bg-[var(--bg)]/70",
                    isLive && "bg-red-500/5"
                  )}
                >
                  {/* Matchup + score */}
                  <td className="px-4 py-3.5">
                    <div className="font-medium text-[var(--text)] flex items-center gap-2">
                      <span>{game.away.abbreviation}</span>
                      <span className="text-[var(--muted)] font-normal">@</span>
                      <span>{game.home.abbreviation}</span>
                    </div>
                    <div className="text-xs text-[var(--muted)] mt-0.5">
                      {showScore ? (
                        <span className="font-medium text-[var(--text)]">
                          {game.score!.away} – {game.score!.home}
                        </span>
                      ) : (
                        `${game.away.name} at ${game.home.name}`
                      )}
                    </div>
                  </td>

                  {/* Kickoff (US Eastern) */}
                  <td className="px-4 py-3.5 whitespace-nowrap text-[var(--text)]">
                    {formatKickoff(game.kickoff)}
                  </td>

                  {/* Status */}
                  <td className="px-4 py-3.5">
                    <StatusBadge status={game.status} />
                  </td>

                  {/* Venue */}
                  {hasVenue && (
                    <td className="px-4 py-3.5 hidden lg:table-cell text-[var(--muted)]">
                      {game.venue || "—"}
                    </td>
                  )}

                  {/* Spread */}
                  <td className="px-4 py-3.5 text-right">
                    <OddsFlashCell
                      value={fmtSpread(game.spread)}
                      className={cn(game.bestSpread && "text-[var(--green)] font-medium")}
                    />
                  </td>

                  {/* Total */}
                  <td className="px-4 py-3.5 text-right">
                    <OddsFlashCell
                      value={fmtTotal(game.total)}
                      className={cn(game.bestTotal && "text-[var(--green)] font-medium")}
                    />
                  </td>

                  {/* Moneyline Home */}
                  <td className="px-4 py-3.5 text-right">
                    <OddsFlashCell
                      value={formatOdds(game.moneylineHome)}
                      className={cn(game.bestMoneylineHome && "text-[var(--green)] font-medium")}
                    />
                  </td>

                  {/* Moneyline Away */}
                  <td className="px-4 py-3.5 text-right">
                    <OddsFlashCell
                      value={formatOdds(game.moneylineAway)}
                      className={cn(game.bestMoneylineAway && "text-[var(--green)] font-medium")}
                    />
                  </td>

                  {/* Move chip */}
                  {hasMove && (
                    <td className="px-4 py-3.5 text-center">
                      {game.spreadMove ? (
                        <span
                          className={cn(
                            "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium tabular-nums",
                            game.spreadMove > 0
                              ? "bg-green-500/15 text-[var(--green)]"
                              : "bg-red-500/15 text-[var(--red)]"
                          )}
                        >
                          {formatMove(game.spreadMove)}
                        </span>
                      ) : (
                        <span className="text-[var(--muted)]">—</span>
                      )}
                    </td>
                  )}

                  {/* Sparkline */}
                  {hasTrend && (
                    <td className="px-4 py-3.5">
                      <div className="flex justify-center">
                        {(game.sparkline?.length ?? 0) > 1 ? (
                          <Sparkline data={game.sparkline ?? []} />
                        ) : (
                          <span className="text-[var(--muted)]">—</span>
                        )}
                      </div>
                    </td>
                  )}
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}