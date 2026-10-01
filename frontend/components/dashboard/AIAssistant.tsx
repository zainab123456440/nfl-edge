"use client";

import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from "react";

/* ───────────── Typing tagline ───────────── */

const LINES = [
  "Spot line moves before the market does.",
  "Ask anything about tonight's slate.",
  "Props, injuries, trends: one question away.",
  "Upload a slip. Get the breakdown.",
];

export function TypingTagline() {
  const [text, setText] = useState("");
  const [i, setI] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const id = setInterval(() => setI((n) => (n + 1) % LINES.length), 3500);
      setText(LINES[i]);
      return () => clearInterval(id);
    }
    const full = LINES[i];
    let delay = deleting ? 18 : 42;
    if (!deleting && text === full) delay = 1900; // hold finished line
    if (deleting && text === "") delay = 350; // beat before next line

    const t = setTimeout(() => {
      if (!deleting && text === full) return setDeleting(true);
      if (deleting && text === "") {
        setDeleting(false);
        return setI((n) => (n + 1) % LINES.length);
      }
      setText(deleting ? full.slice(0, text.length - 1) : full.slice(0, text.length + 1));
    }, delay);
    return () => clearTimeout(t);
  }, [text, deleting, i]);

  return (
    <p className="flex h-6 items-center gap-2 text-sm font-medium text-amber-200/90" aria-label={LINES.join(" ")}>
      <span aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-300 shadow-[0_0_8px_rgba(252,211,77,0.8)]" />
      <span aria-hidden className="truncate">
        {text}
        <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-[3px] animate-pulse bg-amber-300" />
      </span>
    </p>
  );
}

/* ───────────── Assistant ───────────── */

type Msg = { id: number; role: "user" | "assistant"; text: string; files?: string[] };

const SUGGESTIONS = [
  "Which props have the biggest line movement today?",
  "Summarize key injuries for tonight's games",
  "Find hot trends over the last 10 games",
  "Break down the slip I upload",
];

const fmtSize = (b: number) => (b > 1e6 ? `${(b / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1e3))} KB`);

export function AIAssistant() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  }, [input]);

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    setFiles((prev) => [...prev, ...Array.from(list)].slice(0, 5));
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const send = async (override?: string) => {
    const text = (override ?? input).trim();
    if ((!text && files.length === 0) || busy) return;
    const sent = files;
    setMessages((m) => [...m, { id: Date.now(), role: "user", text, files: sent.map((f) => f.name) }]);
    setInput("");
    setFiles([]);
    setBusy(true);

    // TODO: replace with your backend call, e.g.
    // const fd = new FormData(); fd.append("message", text); sent.forEach(f => fd.append("files", f));
    // const res = await fetch("/api/assistant", { method: "POST", body: fd });
    await new Promise((r) => setTimeout(r, 1200));
    setMessages((m) => [
      ...m,
      {
        id: Date.now() + 1,
        role: "assistant",
        text: "Assistant backend isn't connected yet. Once it is, your answer will appear here.",
      },
    ]);
    setBusy(false);
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <section
      aria-label="AI assistant"
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false);
      }}
      onDrop={onDrop}
      className="relative overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950/70 shadow-[0_0_0_1px_rgba(255,255,255,0.02),0_24px_60px_-24px_rgba(0,0,0,0.8)] backdrop-blur"
    >
      {/* soft amber edge light */}
      <div aria-hidden className="pointer-events-none absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-amber-300/50 to-transparent" />

      {/* header */}
      <div className="flex items-center justify-between border-b border-zinc-800/80 px-4 py-3 sm:px-5">
        <div className="flex items-center gap-3">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-amber-300/10 text-amber-300 ring-1 ring-amber-300/20">
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z" />
              <path d="M19 16l.7 1.8L21.5 18.5l-1.8.7L19 21l-.7-1.8-1.8-.7 1.8-.7L19 16z" />
            </svg>
          </div>
          <div>
            <h2 className="text-sm font-medium text-zinc-100">AI assistant</h2>
            <p className="text-xs text-zinc-500">Trends, props, and game insights</p>
          </div>
        </div>
        <span className="flex items-center gap-1.5 text-xs text-zinc-500">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Ready
        </span>
      </div>

      {/* conversation */}
      <div ref={scrollRef} className="h-[340px] overflow-y-auto px-4 py-5 sm:h-[400px] sm:px-5" aria-live="polite">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col justify-end">
            <p className="mb-3 text-sm text-zinc-400">Start with a question, or try one of these.</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-zinc-800 bg-zinc-900/60 px-3.5 py-1.5 text-left text-[13px] text-zinc-300 transition hover:border-amber-300/40 hover:text-amber-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-300"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <ul className="space-y-4">
            {messages.map((m) => (
              <li key={m.id} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={
                    m.role === "user"
                      ? "max-w-[85%] rounded-2xl rounded-br-md bg-amber-300 px-4 py-2.5 text-sm text-zinc-950"
                      : "max-w-[85%] rounded-2xl rounded-bl-md border border-zinc-800 bg-zinc-900/70 px-4 py-2.5 text-sm text-zinc-200"
                  }
                >
                  {m.files && m.files.length > 0 && (
                    <div className="mb-1.5 flex flex-wrap gap-1.5">
                      {m.files.map((f) => (
                        <span key={f} className="rounded-md bg-zinc-950/15 px-2 py-0.5 text-xs">
                          {f}
                        </span>
                      ))}
                    </div>
                  )}
                  {m.text && <p className="whitespace-pre-wrap leading-relaxed">{m.text}</p>}
                </div>
              </li>
            ))}
            {busy && (
              <li className="flex justify-start" aria-label="Assistant is thinking">
                <div className="flex gap-1 rounded-2xl rounded-bl-md border border-zinc-800 bg-zinc-900/70 px-4 py-3">
                  {[0, 150, 300].map((d) => (
                    <span key={d} className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500" style={{ animationDelay: `${d}ms` }} />
                  ))}
                </div>
              </li>
            )}
          </ul>
        )}
      </div>

      {/* composer */}
      <div className="border-t border-zinc-800/80 p-3 sm:p-4">
        {files.length > 0 && (
          <ul className="mb-2.5 flex flex-wrap gap-2">
            {files.map((f, idx) => (
              <li key={f.name + idx} className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900 py-1 pl-2.5 pr-1 text-xs text-zinc-300">
                <span className="max-w-[160px] truncate">{f.name}</span>
                <span className="text-zinc-600">{fmtSize(f.size)}</span>
                <button
                  onClick={() => setFiles((p) => p.filter((_, j) => j !== idx))}
                  aria-label={`Remove ${f.name}`}
                  className="grid h-5 w-5 place-items-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="flex items-end gap-2 rounded-xl border border-zinc-800 bg-zinc-900/60 p-2 transition focus-within:border-amber-300/50 focus-within:ring-4 focus-within:ring-amber-300/5">
          <input ref={fileRef} type="file" multiple hidden onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }} />
          <button
            onClick={() => fileRef.current?.click()}
            aria-label="Attach files"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-zinc-400 transition hover:bg-zinc-800 hover:text-amber-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-300"
          >
            <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M21 11.5l-8.6 8.6a5 5 0 01-7-7l8.6-8.6a3.3 3.3 0 014.7 4.7l-8.6 8.6a1.7 1.7 0 01-2.3-2.4l7.9-7.9" />
            </svg>
          </button>
          <textarea
            ref={taRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            placeholder="Ask about a game, player, prop, or upload a slip…"
            aria-label="Message"
            className="max-h-40 min-h-9 flex-1 resize-none bg-transparent py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
          />
          <button
            onClick={() => send()}
            disabled={busy || (!input.trim() && files.length === 0)}
            aria-label="Send message"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-amber-300 text-zinc-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </div>
        <p className="mt-2 px-1 text-[11px] text-zinc-600">Enter to send · Shift+Enter for a new line · Up to 5 files</p>
      </div>

      {/* drop overlay */}
      {dragging && (
        <div className="absolute inset-0 z-10 grid place-items-center bg-zinc-950/85 backdrop-blur-sm">
          <div className="rounded-xl border border-dashed border-amber-300/60 px-8 py-6 text-center">
            <p className="text-sm font-medium text-amber-200">Drop files to attach</p>
            <p className="mt-1 text-xs text-zinc-500">Slips, screenshots, CSVs, PDFs</p>
          </div>
        </div>
      )}
    </section>
  );
}