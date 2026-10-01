import { getGlanceStats } from "../../lib/api";
import { AIAssistant, TypingTagline } from "../../components/dashboard/AIAssistant";

export const metadata = { title: "Dashboard" };

const fmt = (v: number | null) => (v === null ? "—" : v.toLocaleString());

export default async function DashboardPage() {
  const stats = await getGlanceStats();
  const glance = [
    { label: "Games", value: stats.games },
    { label: "Props", value: stats.props },
    { label: "Line Movement", value: stats.lineMovement },
    { label: "Injuries", value: stats.injuries },
  ];

  return (
    <main className="relative mx-auto w-full max-w-4xl overflow-x-hidden px-4 pb-12 pt-6 sm:px-6 sm:pt-10 lg:pt-12">
      {/* Hero */}
      <header className="relative mb-6 sm:mb-8">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 -top-10 -z-10 h-64 opacity-60 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]"
          style={{
            backgroundImage:
              "radial-gradient(ellipse 60% 70% at 50% 0%, rgba(253,230,138,0.09), transparent 70%), linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
            backgroundSize: "auto, 40px 40px, 40px 40px",
          }}
        />
        <TypingTagline />
        <h1 className="mt-3 max-w-xl text-balance text-2xl font-semibold tracking-tight text-zinc-50 sm:text-3xl lg:text-[2rem] lg:leading-tight">
          Understand the game beyond the numbers.
        </h1>
        <p className="mt-2.5 max-w-lg text-sm leading-relaxed text-zinc-400 sm:text-[15px]">
          Ask questions, explore trends, analyze props, and turn your data into actionable insights.
        </p>
      </header>

      {/* Primary focus */}
      <AIAssistant />

      {/* Supporting info */}
      <section aria-label="At a glance" className="mt-6 sm:mt-8">
        <h2 className="mb-3 text-xs font-medium text-zinc-500">At a glance</h2>
        <dl className="grid grid-cols-2 divide-zinc-800 rounded-xl border border-zinc-800 bg-zinc-950/40 sm:grid-cols-4 sm:divide-x [&>div:nth-child(-n+2)]:border-b [&>div:nth-child(-n+2)]:border-zinc-800 sm:[&>div:nth-child(-n+2)]:border-b-0 [&>div:nth-child(odd)]:border-r [&>div:nth-child(odd)]:border-zinc-800 sm:[&>div:nth-child(odd)]:border-r-0">
          {glance.map((g) => (
            <div key={g.label} className="px-4 py-3.5">
              <dt className="text-xs text-zinc-500">{g.label}</dt>
              <dd className="mt-1 text-lg font-medium tabular-nums text-zinc-200">{fmt(g.value)}</dd>
            </div>
          ))}
        </dl>
      </section>
    </main>
  );
}