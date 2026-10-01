"use client";

import {
  Suspense,
  useState,
  useMemo,
  useCallback,
  useEffect,
} from "react";
import useSWR from "swr";
import {
  useSearchParams,
  useRouter,
  usePathname,
} from "next/navigation";

import FilterBar from "../../components/games/Filterbar";
import GamesTable from "../../components/games/GamesTable";
import BiggestMoves from "../../components/games/BiggestMoves";
import GameSlideOver from "../../components/games/GameSlideOver";

import type { Game, GamesResponse } from "../../lib/type";
import { getGames } from "../../lib/api";
import { getCurrentWeek } from "../../lib/time";
import { useAuth } from "../../Hooks/useAuth";

// Status values (lowercase).
const FINISHED_STATUSES = [
  "final",
  "finished",
  "closed",
  "complete",
  "completed",
];

const LIVE_STATUSES = [
  "live",
  "in_progress",
  "inprogress",
  "in progress",
];

const MIN_WEEK = 1;
const MAX_WEEK = 18;

/* ---------- small building blocks ---------- */

function StatCard({
  label,
  value,
  loading,
  live = false,
}: {
  label: string;
  value: string | number;
  loading?: boolean;
  live?: boolean;
}) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)]/70 px-5 py-4 backdrop-blur">
      <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-[var(--muted)]">
        {live && <span className="live-dot" />}
        {label}
      </p>

      {loading ? (
        <div className="mt-2 h-8 w-16 rounded skeleton" />
      ) : (
        <p className="mt-1 text-3xl font-semibold tabular-nums text-[var(--text)]">
          {value}
        </p>
      )}
    </div>
  );
}

/* ---------- page ---------- */

function GamesContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const {
    isAuthenticated,
    isLoading: authLoading,
  } = useAuth();

  // Current NFL week
  const currentWeek = useMemo(
    () => getCurrentWeek(),
    []
  );

  const urlWeek = searchParams.get("week");
  const week = urlWeek
    ? Number(urlWeek)
    : currentWeek;

  const book =
    searchParams.get("book") || undefined;

  const team =
    searchParams.get("team") || undefined;

  const goToWeek = useCallback(
    (w: number) => {
      const next = Math.min(
        MAX_WEEK,
        Math.max(MIN_WEEK, w)
      );

      const params = new URLSearchParams(
        searchParams.toString()
      );

      params.set("week", String(next));

      router.replace(
        `${pathname}?${params.toString()}`,
        { scroll: false }
      );
    },
    [
      router,
      pathname,
      searchParams,
    ]
  );

  /*
   * Client-side route protection.
   *
   * The backend remains the actual security boundary.
   * This only prevents an unauthenticated user from
   * sitting on the page while the API rejects requests.
   */
  useEffect(() => {
    if (
      !authLoading &&
      !isAuthenticated
    ) {
      router.replace("/login");
    }
  }, [
    authLoading,
    isAuthenticated,
    router,
  ]);

  const swrKey =
    authLoading || !isAuthenticated
      ? null
      : (() => {
          const params =
            new URLSearchParams();

          params.set(
            "week",
            String(week)
          );

          if (book) {
            params.set("book", book);
          }

          if (team) {
            params.set("team", team);
          }

          return `games?${params.toString()}`;
        })();

  const {
    data,
    error,
    isLoading,
  } = useSWR<GamesResponse>(
    swrKey,
    () =>
      getGames({
        week,
        book,
        team,
      }),
    {
      refreshInterval: 30000,
      revalidateOnFocus: true,

      onSuccess: () =>
        setUpdatedAt(new Date()),
    }
  );

  const [updatedAt, setUpdatedAt] =
    useState<Date | null>(null);

  const [
    selectedGame,
    setSelectedGame,
  ] = useState<Game | null>(null);

  const [
    slideOverOpen,
    setSlideOverOpen,
  ] = useState(false);

  const handleRowClick = (
    game: Game
  ) => {
    setSelectedGame(game);
    setSlideOverOpen(true);
  };

  const handleCloseSlideOver = () => {
    setSlideOverOpen(false);

    setTimeout(() => {
      setSelectedGame(null);
    }, 300);
  };

  /* ---------- derived data ---------- */

  const games = data?.games ?? [];

  const moves = (
    data?.biggestMoves ?? []
  ).filter(
    (m) => Math.abs(m.amount) > 0
  );

  const stats = data?.stats;

  const hasMoves =
    moves.length > 0;

  const liveCount =
    data?.liveCount ?? 0;

  // Upcoming games this week
  const upcoming = useMemo(() => {
    const list =
      games as unknown as {
        kickoff?: string;
        status?: string;
      }[];

    return list
      .filter((g) => {
        const s = String(
          g.status ?? ""
        ).toLowerCase();

        return (
          g.kickoff &&
          !FINISHED_STATUSES.includes(s) &&
          !LIVE_STATUSES.includes(s) &&
          new Date(
            g.kickoff
          ).getTime() > Date.now()
        );
      })
      .sort(
        (a, b) =>
          +new Date(a.kickoff!) -
          +new Date(b.kickoff!)
      );
  }, [games]);

  const upcomingCount =
    upcoming.length;

  const nextKickoff =
    upcoming[0]?.kickoff ?? null;

  const biggestMove =
    stats?.biggestMove &&
    Math.abs(
      stats.biggestMove
    ) > 0
      ? `${
          stats.biggestMove > 0
            ? "+"
            : ""
        }${stats.biggestMove} pts`
      : "--";

  const averageTotal =
    stats?.averageTotal
      ? Number(
          stats.averageTotal
        ).toFixed(1)
      : "--";

  const weekStatus =
    week === currentWeek
      ? "Current week"
      : week < currentWeek
        ? "Archived"
        : "Upcoming";

  const isLive =
    liveCount > 0;

  /*
   * Avoid rendering protected data while auth
   * state is still being restored.
   */
  if (
    authLoading ||
    !isAuthenticated
  ) {
    return (
      <div className="flex min-h-screen items-center justify-center text-[var(--muted)]">
        Loading games...
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <main className="mx-auto w-full max-w-[1600px] space-y-6 px-4 py-6 sm:px-6 md:px-8">
        {/* HERO HEADER */}
        <section className="relative overflow-hidden rounded-3xl border border-[var(--border)] bg-[var(--card)] p-6 sm:p-10">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-[var(--blue)]/20 blur-3xl"
          />

          <div
            aria-hidden
            className="pointer-events-none absolute -bottom-32 left-1/3 h-72 w-72 rounded-full bg-[var(--blue)]/10 blur-3xl"
          />

          <div className="relative space-y-8">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:gap-8">
              {/* BIG WEEK NUMBER */}
              <div className="flex h-28 w-28 shrink-0 flex-col items-center justify-center rounded-3xl border border-[var(--blue)]/40 bg-[var(--blue)]/10 shadow-[0_0_48px_-12px_var(--blue)] sm:h-36 sm:w-36">
                <span className="text-xs font-semibold tracking-widest text-[var(--blue)]/80">
                  WEEK
                </span>

                <span className="text-6xl font-bold leading-none tabular-nums text-[var(--blue)] sm:text-7xl">
                  {week}
                </span>
              </div>

              <div className="min-w-0 max-w-2xl">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  {isLive ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-red-500/30 bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-400">
                      <span className="live-dot" />
                      {liveCount} live now
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400">
                      <span className="relative flex h-2 w-2">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                      </span>
                      Live lines
                    </span>
                  )}

                  <span className="rounded-full border border-[var(--border)] bg-[var(--card)]/70 px-2.5 py-1 text-xs font-medium text-[var(--muted)]">
                    {weekStatus}
                  </span>

                  {updatedAt && (
                    <span className="text-xs text-[var(--muted)]">
                      Updated{" "}
                      {updatedAt.toLocaleTimeString(
                        [],
                        {
                          hour: "numeric",
                          minute: "2-digit",
                        }
                      )}
                    </span>
                  )}
                </div>

                <h1 className="text-4xl font-bold tracking-tight text-[var(--text)] sm:text-5xl">
                  Games
                </h1>

                <p className="mt-3 text-sm leading-relaxed text-[var(--muted)] sm:text-base">
                  Live lines, the biggest
                  moves and matchup detail
                  for every game on the
                  slate.

                  {!isLive &&
                    upcomingCount > 0 &&
                    nextKickoff && (
                      <>
                        {" "}
                        Next kickoff{" "}
                        <span className="font-medium text-[var(--text)]">
                          {new Date(
                            nextKickoff
                          ).toLocaleString(
                            [],
                            {
                              weekday:
                                "short",
                              hour:
                                "numeric",
                              minute:
                                "2-digit",
                            }
                          )}
                        </span>
                        .
                      </>
                    )}
                </p>
              </div>
            </div>

            {/* QUICK STATS */}
            <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
              <StatCard
                label="Games"
                value={
                  stats?.gamesThisWeek ??
                  games.length
                }
                loading={isLoading}
              />

              <StatCard
                label="Live now"
                value={
                  stats?.liveNow ??
                  liveCount
                }
                loading={isLoading}
                live={isLive}
              />

              <StatCard
                label="Biggest move"
                value={biggestMove}
                loading={isLoading}
              />

              <StatCard
                label="Avg total"
                value={averageTotal}
                loading={isLoading}
              />
            </div>
          </div>
        </section>

        {/* FILTERS */}
        <section className="rounded-2xl border border-[var(--border)] bg-[var(--card)]/60 p-4 sm:p-5">
          <h2 className="mb-3 text-sm font-semibold text-[var(--text)]">
            Filters
          </h2>

          <FilterBar />
        </section>

        {/* MAIN CONTENT */}
        <div
          className={
            hasMoves
              ? "grid grid-cols-1 gap-6 xl:grid-cols-[1fr_320px]"
              : "grid grid-cols-1 gap-6"
          }
        >
          <div className="min-w-0">
            {isLoading ? (
              <div className="space-y-3 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6">
                {[
                  1, 2, 3, 4,
                  5, 6, 7, 8,
                ].map((i) => (
                  <div
                    key={i}
                    className="h-12 rounded-lg skeleton"
                  />
                ))}
              </div>
            ) : error ? (
              <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-10 text-center">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-red-500/15 text-xl text-red-400">
                  !
                </div>

                <p className="text-lg font-semibold text-red-400">
                  Failed to load games
                </p>

                <p className="mt-1 text-sm text-[var(--muted)]">
                  {error.message ||
                    "Please check your API connection"}
                </p>
              </div>
            ) : games.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-[var(--border)] bg-[var(--card)] p-12 text-center">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--blue)]/10 text-xl text-[var(--blue)]">
                  ?
                </div>

                <p className="text-lg font-semibold text-[var(--text)]">
                  No games found for
                  Week {week}
                </p>

                <p className="mx-auto mt-1 max-w-sm text-sm text-[var(--muted)]">
                  {week > currentWeek
                    ? "Lines will appear here once the sportsbooks post them."
                    : "Try another week or clear your filters."}
                </p>

                {week !== currentWeek && (
                  <button
                    type="button"
                    onClick={() =>
                      goToWeek(
                        currentWeek
                      )
                    }
                    className="mt-5 rounded-lg bg-[var(--blue)] px-4 py-2 text-sm font-medium text-slate-900 transition hover:opacity-90"
                  >
                    Go to Week{" "}
                    {currentWeek}
                  </button>
                )}
              </div>
            ) : (
              <div className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-lg shadow-black/10">
                <GamesTable
                  games={games}
                  onRowClick={
                    handleRowClick
                  }
                />
              </div>
            )}
          </div>

          {hasMoves && (
            <div className="hidden xl:block">
              {isLoading ? (
                <div className="h-96 rounded-2xl skeleton" />
              ) : (
                <div className="sticky top-6 overflow-hidden rounded-2xl shadow-lg shadow-black/10">
                  <BiggestMoves
                    moves={moves}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* GAME DETAILS */}
      <GameSlideOver
        game={selectedGame}
        open={slideOverOpen}
        onClose={
          handleCloseSlideOver
        }
      />
    </div>
  );
}

export default function GamesPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-[var(--muted)]">
          Loading games...
        </div>
      }
    >
      <GamesContent />
    </Suspense>
  );
}