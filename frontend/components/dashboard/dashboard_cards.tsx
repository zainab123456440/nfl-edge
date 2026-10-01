"use client";

import Link from "next/link";

export default function DashboardCards() {
return ( <section className="mt-6 space-y-5">
{/* Main navigation banner */} <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900 via-slate-950 to-black p-6 shadow-xl sm:p-8"> <div className="pointer-events-none absolute -right-5 -top-8 rotate-[-20deg] text-[120px] opacity-[0.08]">
🏈 </div>

```
    <div className="pointer-events-none absolute bottom-[-35px] right-[35%] rotate-[25deg] text-[75px] opacity-[0.04]">
      🏈
    </div>

    <div className="relative z-10 max-w-2xl">
      <div className="mb-3 flex items-center gap-2">
        <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
        <span className="text-xs font-medium uppercase tracking-wider text-emerald-300">
          NFL Edge
        </span>
      </div>

      <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
        Your edge starts here.
      </h2>

      <p className="mt-2 text-sm leading-6 text-slate-400 sm:text-base">
        Explore live games, player props, market movement and everything
        you need before kickoff.
      </p>

      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          href="/games"
          className="rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:-translate-y-0.5 hover:bg-slate-200"
        >
          Explore Games →
        </Link>

        <Link
          href="/props"
          className="rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-white/10"
        >
          Explore Props →
        </Link>
      </div>
    </div>
  </div>

  {/* Navigation cards */}
  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
    <Link
      href="/games"
      className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.035] p-6 transition duration-200 hover:-translate-y-1 hover:border-white/20 hover:bg-white/[0.06]"
    >
      <div className="absolute -right-8 -top-8 text-7xl opacity-[0.05] transition group-hover:scale-110 group-hover:opacity-[0.08]">
        🏟️
      </div>

      <div className="relative">
        <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/10 text-2xl">
          🏟️
        </div>

        <h3 className="text-lg font-semibold text-white">
          Games & Matchups
        </h3>

        <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
          Check upcoming matchups, teams, kickoff times and available
          market information.
        </p>

        <div className="mt-5 text-sm font-medium text-slate-400 transition group-hover:text-white">
          View Games →
        </div>
      </div>
    </Link>

    <Link
      href="/props"
      className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.035] p-6 transition duration-200 hover:-translate-y-1 hover:border-white/20 hover:bg-white/[0.06]"
    >
      <div className="absolute -right-8 -top-8 text-7xl opacity-[0.05] transition group-hover:scale-110 group-hover:opacity-[0.08]">
        📊
      </div>

      <div className="relative">
        <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 text-2xl">
          📊
        </div>

        <h3 className="text-lg font-semibold text-white">
          Player Props
        </h3>

        <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
          Browse passing, rushing, receiving, touchdown and other player
          markets.
        </p>

        <div className="mt-5 text-sm font-medium text-slate-400 transition group-hover:text-white">
          Browse Props →
        </div>
      </div>
    </Link>
  </div>

  {/* Feature strip */}
  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
    <Link
      href="/props"
      className="rounded-2xl border border-white/10 bg-white/[0.025] px-5 py-4 transition hover:bg-white/[0.05]"
    >
      <div className="text-lg">📈</div>
      <p className="mt-2 text-sm font-medium text-white">
        Market Movement
      </p>
      <p className="mt-1 text-xs text-slate-500">
        Track changing lines
      </p>
    </Link>

    <Link
      href="/games"
      className="rounded-2xl border border-white/10 bg-white/[0.025] px-5 py-4 transition hover:bg-white/[0.05]"
    >
      <div className="text-lg">🏥</div>
      <p className="mt-2 text-sm font-medium text-white">
        Injury Updates
      </p>
      <p className="mt-1 text-xs text-slate-500">
        Stay ahead of news
      </p>
    </Link>

    <Link
      href="/dashboard"
      className="rounded-2xl border border-emerald-400/10 bg-emerald-400/[0.035] px-5 py-4 transition hover:bg-emerald-400/[0.07]"
    >
      <div className="text-lg">🤖</div>
      <p className="mt-2 text-sm font-medium text-white">
        AI Assistant
      </p>
      <p className="mt-1 text-xs text-slate-500">
        Ask about your slate
      </p>
    </Link>
  </div>
</section>
);
}