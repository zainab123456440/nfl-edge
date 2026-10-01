// app/props/page.tsx
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

import PropsFilters from "../../components/props/Propsfilters";
import PropsBoard from "../../components/props/PropBoard";
import PropDetailPanel from "../../components/props/PropDetailpanel";

import type { BoardRow } from "../../types/props";
import {
  getBoard,
  getMarkets,
} from "../../lib/propapi";
import { getCurrentWeek } from "../../lib/time";
import { useAuth } from "../../Hooks/useAuth";

// Keys must match what your API returns exactly.
const MAIN_BOOKS: [string, string][] = [
  ["draftkings", "DraftKings"],
  ["fanduel", "FanDuel"],
  ["betmgm", "BetMGM"],
  ["caesars", "Caesars"],
];

function StatCard({
  label,
  value,
  loading,
}: {
  label: string;
  value: string | number;
  loading?: boolean;
}) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)]/70 px-4 py-3 backdrop-blur">
      <p className="text-[11px] font-medium uppercase tracking-wider text-[var(--muted)]">
        {label}
      </p>

      {loading ? (
        <div className="mt-1.5 h-6 w-14 rounded skeleton" />
      ) : (
        <p className="mt-0.5 text-xl font-semibold tabular-nums text-[var(--text)]">
          {value}
        </p>
      )}
    </div>
  );
}

function PropsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const {
    isAuthenticated,
    isLoading: authLoading,
  } = useAuth();

  /*
   * Always the current week.
   * It moves forward automatically each NFL week.
   */
  const week = useMemo(
    () => getCurrentWeek(),
    []
  );

  const filters = {
    market:
      searchParams.get("market") || "",
    book:
      searchParams.get("book") || "",
    search:
      searchParams.get("search") || "",
  };

  const hasFilters = Boolean(
    filters.market ||
      filters.book ||
      filters.search
  );

  /*
   * Protect the client page.
   *
   * The FastAPI backend remains the real security
   * boundary. This prevents unnecessary API requests
   * while the frontend auth state is being restored.
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

  const setParam = useCallback(
    (
      key: string,
      value: string
    ) => {
      const params =
        new URLSearchParams(
          searchParams.toString()
        );

      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }

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

  const clearFilters = useCallback(() => {
    router.replace(pathname, {
      scroll: false,
    });
  }, [router, pathname]);

  const [updatedAt, setUpdatedAt] =
    useState<Date | null>(null);

  /*
   * Do not query protected/shared API endpoints
   * until authentication has been restored.
   */
  const swrEnabled =
    !authLoading &&
    isAuthenticated;

  const {
    data: markets = [],
  } = useSWR(
    swrEnabled
      ? "props/markets"
      : null,
    getMarkets
  );

  const {
    data: rows,
    error,
    isLoading,
  } = useSWR<BoardRow[]>(
    swrEnabled
      ? `props/board?week=${week}&${JSON.stringify(
          filters
        )}`
      : null,
    () =>
      getBoard({
        week,
        ...filters,
      }),
    {
      refreshInterval: 60000,
      revalidateOnFocus: true,

      onSuccess: () =>
        setUpdatedAt(new Date()),
    }
  );

  const [
    selected,
    setSelected,
  ] = useState<BoardRow | null>(
    null
  );

  const [
    open,
    setOpen,
  ] = useState(false);

  /*
   * Board columns: only main books that actually
   * appear in the data.
   *
   * Tolerates different field names / casing:
   * DraftKings, draft_kings, draftkings, etc.
   */
  const {
    bookOptions,
    bookCount,
  } = useMemo(() => {
    const present =
      new Set<string>();

    const norm = (
      v: unknown
    ) =>
      String(v ?? "")
        .toLowerCase()
        .replace(/[\s_-]/g, "");

    (rows ?? []).forEach(
      (r) =>
        (
          (r as any).books ??
          []
        ).forEach(
          (b: any) => {
            const id =
              b.key ??
              b.book ??
              b.bookmaker ??
              b.bookmaker_key ??
              b.sportsbook ??
              b.name;

            if (id) {
              present.add(
                norm(id)
              );
            }
          }
        )
    );

    return {
      bookOptions:
        MAIN_BOOKS.filter(
          ([k]) =>
            present.has(norm(k))
        ),

      bookCount:
        present.size,
    };
  }, [rows]);

  /*
   * Auth is still being restored.
   */
  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-[var(--muted)]">
        Loading props...
      </div>
    );
  }

  /*
   * User is not authenticated.
   * Redirect effect above handles navigation.
   */
  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center text-[var(--muted)]">
        Redirecting to login...
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <main className="mx-auto w-full max-w-[1600px] space-y-6 px-4 py-6 sm:px-6 md:px-8">
        {/* HERO HEADER */}
        <section className="relative overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 sm:p-8">
          {/* soft glow */}
          <div
            aria-hidden
            className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-[var(--blue)]/20 blur-3xl"
          />

          <div
            aria-hidden
            className="pointer-events-none absolute -bottom-32 left-1/3 h-64 w-64 rounded-full bg-[var(--blue)]/10 blur-3xl"
          />

          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                  </span>
                  Live odds
                </span>

                <span className="rounded-full border border-[var(--blue)]/40 bg-[var(--blue)]/10 px-2.5 py-1 text-xs font-semibold text-[var(--blue)]">
                  Week {week}
                </span>
              </div>

              <h1 className="text-3xl font-bold tracking-tight text-[var(--text)] sm:text-4xl">
                Player props
              </h1>

              <p className="mt-2 text-sm leading-relaxed text-[var(--muted)] sm:text-base">
                Every sportsbook side by
                side. Compare lines, spot
                the best price and check hit
                rates over the last 10 games.
              </p>
            </div>

            {/* QUICK STATS */}
            <div className="grid grid-cols-3 gap-3 lg:w-[420px]">
              <StatCard
                label="Props"
                value={(
                  rows?.length ?? 0
                ).toLocaleString()}
                loading={isLoading}
              />

              <StatCard
                label="Sportsbooks"
                value={
                  bookOptions.length
                }
                loading={isLoading}
              />

              <StatCard
                label="Updated"
                value={
                  updatedAt
                    ? updatedAt.toLocaleTimeString(
                        [],
                        {
                          hour: "numeric",
                          minute: "2-digit",
                        }
                      )
                    : "--"
                }
                loading={
                  isLoading &&
                  !updatedAt
                }
              />
            </div>
          </div>
        </section>

        {/* FILTERS */}
        <section className="rounded-2xl border border-[var(--border)] bg-[var(--card)]/60 p-4 sm:p-5">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-[var(--text)]">
              Filters
            </h2>

            {hasFilters && (
              <button
                type="button"
                onClick={
                  clearFilters
                }
                className="rounded-lg border border-[var(--border)] px-3 py-1 text-xs font-medium text-[var(--muted)] transition hover:border-[var(--blue)]/50 hover:text-[var(--text)]"
              >
                Clear all
              </button>
            )}
          </div>

          <PropsFilters
            markets={markets}
            filters={filters}
            books={MAIN_BOOKS}
            onChange={setParam}
          />
        </section>

        {/* LOADING */}
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
          /* ERROR */
          <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-10 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-red-500/15 text-xl text-red-400">
              !
            </div>

            <p className="text-lg font-semibold text-red-400">
              Failed to load props
            </p>

            <p className="mt-1 text-sm text-[var(--muted)]">
              {error.message ||
                "Please check your API connection"}
            </p>
          </div>
        ) : !rows ||
          rows.length === 0 ? (
          /* EMPTY */
          <div className="rounded-2xl border border-dashed border-[var(--border)] bg-[var(--card)] p-12 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--blue)]/10 text-xl text-[var(--blue)]">
              ?
            </div>

            <p className="text-lg font-semibold text-[var(--text)]">
              No props found
            </p>

            <p className="mx-auto mt-1 max-w-sm text-sm text-[var(--muted)]">
              {hasFilters
                ? "Nothing matches these filters. Try another market or sportsbook, or clear the filters."
                : `Props for Week ${week} aren't posted yet. Check back soon.`}
            </p>

            {hasFilters && (
              <button
                type="button"
                onClick={
                  clearFilters
                }
                className="mt-5 rounded-lg bg-[var(--blue)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          /* PROPS BOARD */
          <div className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-lg shadow-black/10">
            <PropsBoard
              rows={rows}
              books={bookOptions}
              onRowClick={(r) => {
                setSelected(r);
                setOpen(true);
              }}
            />
          </div>
        )}
      </main>

      {/* DETAIL PANEL */}
      <PropDetailPanel
        row={selected}
        open={open}
        onClose={() => {
          setOpen(false);

          setTimeout(() => {
            setSelected(null);
          }, 300);
        }}
      />
    </div>
  );
}

export default function PropsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-[var(--muted)]">
          Loading props...
        </div>
      }
    >
      <PropsContent />
    </Suspense>
  );
}