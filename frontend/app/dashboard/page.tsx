// app/dashboard/page.tsx

import {
  AIAssistant,
  TypingTagline,
} from "../../components/dashboard/AIAssistant";
import DashboardCards from "../../components/dashboard/dashboard_cards";

export const metadata = {
  title: "Dashboard",
};

export default function DashboardPage() {
  return (
    <main className="relative w-full overflow-x-hidden px-4 pb-10 pt-5 sm:px-6 sm:pt-7 lg:px-8 lg:pt-8">
      {/* Compact hero */}
      <header className="relative mb-5 sm:mb-6">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 -top-8 -z-10 h-48 opacity-50 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]"
          style={{
            backgroundImage:
              "radial-gradient(ellipse 55% 60% at 50% 0%, rgba(59,130,246,0.12), transparent 70%), linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
            backgroundSize: "auto, 40px 40px, 40px 40px",
          }}
        />

        <TypingTagline />

        <h1 className="mt-2.5 max-w-2xl text-balance text-2xl font-semibold tracking-tight text-zinc-50 sm:text-3xl">
          Understand the game beyond the numbers.
        </h1>

        <p className="mt-2 max-w-xl text-sm leading-relaxed text-zinc-400 sm:text-[15px]">
          Ask questions, explore trends, analyze props, and turn your data into
          actionable insights.
        </p>
      </header>

      <AIAssistant />

      <DashboardCards />
    </main>
  );
}