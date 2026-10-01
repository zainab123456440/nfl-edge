"use client";

import { ReactNode } from "react";
import { Trophy } from "lucide-react";

type AuthLayoutProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
};

/** Small SVG football (leather body, white stripes, laces). */
function Football({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg
      viewBox="0 0 100 60"
      className={className}
      style={style}
      aria-hidden="true"
      fill="none"
    >
      <ellipse cx="50" cy="30" rx="48" ry="26" fill="#8a4b22" />
      <ellipse cx="50" cy="30" rx="48" ry="26" stroke="#5c2f12" strokeWidth="2" />
      <path d="M22 8 Q17 30 22 52" stroke="#f5f5f5" strokeWidth="3" />
      <path d="M78 8 Q83 30 78 52" stroke="#f5f5f5" strokeWidth="3" />
      <path d="M36 30 H64" stroke="#f5f5f5" strokeWidth="2.5" strokeLinecap="round" />
      <path
        d="M42 24 V36 M50 24 V36 M58 24 V36"
        stroke="#f5f5f5"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

const footballs = [
  { cls: "af-a", pos: "left-[6%] top-[18%] w-14 opacity-30" },
  { cls: "af-b", pos: "right-[8%] top-[62%] w-12 opacity-25" },
  { cls: "af-c", pos: "left-[68%] top-[8%] w-8 opacity-20" },
  { cls: "af-d", pos: "left-[12%] top-[74%] w-9 opacity-20" },
  { cls: "af-e", pos: "right-[22%] top-[28%] w-7 opacity-15" },
];

export default function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: AuthLayoutProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#050b18] text-white">
      {/* Background */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_15%,rgba(37,99,235,0.22),transparent_45%)]" />
        <div className="absolute -left-24 top-[15%] h-72 w-72 rounded-full bg-blue-600/10 blur-3xl" />
        <div className="absolute -right-24 bottom-[8%] h-80 w-80 rounded-full bg-cyan-500/10 blur-3xl" />

        {/* Field lines */}
        <div className="absolute inset-0 opacity-[0.04]">
          {["left-1/4", "left-1/2", "left-3/4"].map((p) => (
            <div key={p} className={`absolute ${p} h-full w-px bg-white`} />
          ))}
          {["top-1/4", "top-1/2", "top-3/4"].map((p) => (
            <div key={p} className={`absolute ${p} h-px w-full bg-white`} />
          ))}
        </div>

        {/* Moving footballs */}
        {footballs.map((f) => (
          <div key={f.cls} className={`absolute ${f.pos}`}>
            <Football className={`w-full ${f.cls}`} />
          </div>
        ))}
      </div>

      {/* Content */}
      <main className="relative z-10 flex min-h-screen items-center justify-center px-5 py-10">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-blue-400/20 bg-blue-500/10 shadow-lg shadow-blue-500/10">
              <Trophy className="h-7 w-7 text-blue-400" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight">
              NFL<span className="text-blue-400">-EDGE</span>
            </h1>
            <p className="mt-2 text-sm text-slate-400">Your edge starts here.</p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-6 shadow-2xl shadow-black/40 backdrop-blur-xl sm:p-8">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-white">{title}</h2>
              {subtitle && (
                <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
              )}
            </div>
            {children}
          </div>

          {footer && (
            <div className="mt-6 text-center text-sm text-slate-400">{footer}</div>
          )}
          <p className="mt-6 text-center text-xs text-slate-600">
            NFL-EDGE • Data-driven sports insights
          </p>
        </div>
      </main>

      <style jsx>{`
        @keyframes afPass {
          0%   { transform: translate(0, 0) rotate(-15deg); }
          50%  { transform: translate(180px, 70px) rotate(165deg); }
          100% { transform: translate(0, 0) rotate(345deg); }
        }
        @keyframes afPassBack {
          0%   { transform: translate(0, 0) rotate(10deg); }
          50%  { transform: translate(-120px, -80px) rotate(-170deg); }
          100% { transform: translate(0, 0) rotate(-350deg); }
        }
        @keyframes afSpiral {
          0%, 100% { transform: translateY(0) rotate(-25deg); }
          50%      { transform: translateY(-28px) rotate(25deg); }
        }
        :global(.af-a) { animation: afPass 14s ease-in-out infinite; }
        :global(.af-b) { animation: afPassBack 18s ease-in-out infinite; }
        :global(.af-c) { animation: afSpiral 6s ease-in-out infinite; }
        :global(.af-d) { animation: afPass 22s ease-in-out infinite reverse; }
        :global(.af-e) { animation: afSpiral 8s ease-in-out infinite 1s; }

        @keyframes afShake {
          0%, 100% { transform: translateX(0); }
          20%, 60% { transform: translateX(-6px); }
          40%, 80% { transform: translateX(6px); }
        }
        :global(.af-shake) { animation: afShake 0.4s ease-in-out; }

        @media (prefers-reduced-motion: reduce) {
          :global(.af-a), :global(.af-b), :global(.af-c),
          :global(.af-d), :global(.af-e), :global(.af-shake) { animation: none; }
        }
      `}</style>
    </div>
  );
}