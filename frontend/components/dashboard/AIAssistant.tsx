"use client";

import {
  useEffect,
  useRef,
  useState,
  type DragEvent,
  type KeyboardEvent,
} from "react";

import {
  getValidAccessToken,
  refreshAccessToken,
} from "../../services/AuthAPI";

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
      const id = setInterval(
        () => setI((n) => (n + 1) % LINES.length),
        3500
      );

      setText(LINES[i]);

      return () => clearInterval(id);
    }

    const full = LINES[i];
    let delay = deleting ? 18 : 42;

    if (!deleting && text === full) delay = 1900;
    if (deleting && text === "") delay = 350;

    const t = setTimeout(() => {
      if (!deleting && text === full) {
        return setDeleting(true);
      }

      if (deleting && text === "") {
        setDeleting(false);
        return setI((n) => (n + 1) % LINES.length);
      }

      setText(
        deleting
          ? full.slice(0, text.length - 1)
          : full.slice(0, text.length + 1)
      );
    }, delay);

    return () => clearTimeout(t);
  }, [text, deleting, i]);

  return (
    <p
      className="flex h-6 items-center gap-2 text-sm font-medium text-sky-300/90"
      aria-label={LINES.join(" ")}
    >
      <span
        aria-hidden
        className="h-1.5 w-1.5 shrink-0 rounded-full bg-sky-400 shadow-[0_0_8px_rgba(56,189,248,0.7)]"
      />

      <span aria-hidden className="truncate">
        {text}
        <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-[3px] animate-pulse bg-sky-400" />
      </span>
    </p>
  );
}

/* ───────────── Types & helpers ───────────── */

type GeneratedFile = {
  id: string;
  name: string;
  mime_type?: string;
  size_bytes?: number;
  is_generated?: boolean;
  created_at?: string;
};

type Msg = {
  id: string;
  role: "user" | "assistant";
  text: string;
  files?: string[];
  generatedFiles?: GeneratedFile[];
};

const SUGGESTIONS = [
  "Which props have the biggest line movement today?",
  "Summarize key injuries for tonight's games",
  "Find hot trends over the last 10 games",
  "Break down the slip I upload",
];

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/* ───────────── Authentication helpers ───────────── */

/**
 * Build authenticated headers using the current valid access token.
 *
 * getValidAccessToken() automatically refreshes an access token
 * when it is expired or close to expiry.
 */
async function getAuthHeaders(): Promise<HeadersInit> {
  const token = await getValidAccessToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

/**
 * Perform an authenticated request with one automatic auth retry.
 *
 * Flow:
 *
 * getValidAccessToken()
 *        ↓
 * request
 *        ↓
 * 401?
 *   ↓ yes
 * refreshAccessToken()
 *        ↓
 * retry once
 */
async function authenticatedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  let headers = await getAuthHeaders();

  let response = await fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...(options.headers || {}),
    },
  });

  /*
   * Unexpected 401.
   *
   * getValidAccessToken() should normally prevent this, but a token
   * can expire/revoke between validation and the actual request.
   *
   * Refresh once and retry.
   */
  if (response.status === 401) {
    const refreshedToken = await refreshAccessToken();

    if (!refreshedToken) {
      throw new Error("SESSION_EXPIRED");
    }

    headers = {
      ...headers,
      Authorization: `Bearer ${refreshedToken}`,
    };

    response = await fetch(url, {
      ...options,
      headers: {
        ...headers,
        ...(options.headers || {}),
      },
    });
  }

  return response;
}

const fmtSize = (b?: number) => {
  if (!b || b <= 0) return "";

  return b > 1e6
    ? `${(b / 1e6).toFixed(1)} MB`
    : `${Math.max(1, Math.round(b / 1e3))} KB`;
};

function fileType(file: GeneratedFile): string {
  const name = file.name || "";

  const ext = name.includes(".")
    ? name.split(".").pop()?.toUpperCase()
    : "";

  if (ext) return ext;

  if (file.mime_type?.includes("spreadsheet")) return "XLSX";
  if (file.mime_type?.includes("csv")) return "CSV";
  if (file.mime_type?.includes("json")) return "JSON";
  if (file.mime_type?.includes("pdf")) return "PDF";
  if (file.mime_type?.startsWith("text/")) return "TEXT";

  return "FILE";
}

/* ───────────── Assistant ───────────── */

export function AIAssistant() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [dragging, setDragging] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [downloadingFileId, setDownloadingFileId] = useState<string | null>(
    null
  );

  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  /*
   * Tracks whether the current stream already produced usable output.
   *
   * This prevents a late SSE timeout/error from turning an otherwise
   * successful assistant response or generated file into a frontend error.
   */
  const streamSucceededRef = useRef(false);
  const generatedFilesReceivedRef = useRef(0);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, busy, status]);

  useEffect(() => {
    const ta = taRef.current;

    if (!ta) return;

    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  }, [input]);

  const addFiles = (list: FileList | null) => {
    if (!list) return;

    setFiles((prev) => [...prev, ...Array.from(list)].slice(0, 10));
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  };

  /* ───────────── Generated file download ───────────── */

  const downloadGeneratedFile = async (file: GeneratedFile) => {
    if (!file.id || downloadingFileId) return;

    setDownloadingFileId(file.id);

    try {
      const res = await authenticatedFetch(
        `${API_BASE}/assistant/files/${encodeURIComponent(file.id)}/download`,
        {
          method: "GET",
        }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));

        throw new Error(
          err.detail || `Could not download file (${res.status})`
        );
      }

      const data = await res.json();

      if (!data?.url) {
        throw new Error("The server did not return a download URL.");
      }

      /*
       * Use an anchor instead of window.open so the browser treats this
       * as an actual file download when Supabase provides the signed URL.
       */
      const anchor = document.createElement("a");

      anchor.href = data.url;
      anchor.download = file.name || "download";
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";

      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    } catch (err: any) {
      /*
       * Do not expose the internal authentication error to the user.
       */
      if (err?.message === "SESSION_EXPIRED") {
        setMessages((m) => [
          ...m,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            text: "Your session has expired. Please sign in again.",
          },
        ]);

        return;
      }

      console.error("File download failed:", err);

      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: `I couldn't download ${file.name || "the file"}. ${
            err?.message || "Please try again."
          }`,
        },
      ]);
    } finally {
      setDownloadingFileId(null);
    }
  };

  /* ───────────── Send ───────────── */

  const send = async (override?: string) => {
    const text = (override ?? input).trim();

    if ((!text && files.length === 0) || busy) return;

    /*
     * Reset stream state for this request.
     */
    streamSucceededRef.current = false;
    generatedFilesReceivedRef.current = 0;

    const sentFiles = [...files];
    const userMsgId = crypto.randomUUID();

    // Optimistic user message
    setMessages((m) => [
      ...m,
      {
        id: userMsgId,
        role: "user",
        text,
        files: sentFiles.map((f) => f.name),
      },
    ]);

    setInput("");
    setFiles([]);
    setBusy(true);
    setStatus("Thinking…");

    try {
      // -------------------------------------------------------
      // 1. Upload + register files (if any)
      // -------------------------------------------------------
      // Existing upload flow remains unchanged here.
      // Backend currently receives file_ids.
      const fileIds: string[] = [];

      // -------------------------------------------------------
      // 2. Call streaming chat endpoint
      // -------------------------------------------------------

      const res = await authenticatedFetch(
        `${API_BASE}/assistant/chat`,
        {
          method: "POST",
          body: JSON.stringify({
            message: text,
            file_ids: fileIds,
            conversation_id: conversationId,
          }),
        }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));

        throw new Error(
          err.detail || `Request failed (${res.status})`
        );
      }

      if (!res.body) {
        throw new Error("No response body");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";
      let assistantText = "";

      const assistantMsgId = crypto.randomUUID();

      // Add empty assistant message that we will fill
      setMessages((m) => [
        ...m,
        {
          id: assistantMsgId,
          role: "assistant",
          text: "",
          generatedFiles: [],
        },
      ]);

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          const line = part.trim();

          if (!line.startsWith("data: ")) continue;

          let event: any;

          try {
            event = JSON.parse(line.slice(6));
          } catch {
            // Ignore malformed SSE payloads.
            continue;
          }

          /* Conversation */
          if (event.type === "conversation") {
            if (event.conversation_id) {
              setConversationId(event.conversation_id);
            }

            continue;
          }

          /* Status / progress */
          if (
            event.type === "status" ||
            event.type === "thinking"
          ) {
            setStatus(
              event.message ||
                event.content ||
                "Working…"
            );

            continue;
          }

          /* Streaming text */
          if (
            event.type === "token" ||
            event.type === "content" ||
            event.type === "delta"
          ) {
            const chunk =
              event.content ||
              event.delta ||
              event.text ||
              "";

            if (chunk) {
              assistantText += chunk;

              /*
               * We have received usable assistant output.
               */
              streamSucceededRef.current = true;

              setMessages((m) =>
                m.map((msg) =>
                  msg.id === assistantMsgId
                    ? {
                        ...msg,
                        text: assistantText,
                      }
                    : msg
                )
              );
            }

            setStatus("");
            continue;
          }

          /* Full assistant message */
          if (
            event.type === "message" &&
            event.role === "assistant"
          ) {
            const content = event.content || "";

            if (content) {
              assistantText = content;
              streamSucceededRef.current = true;
            }

            setMessages((m) =>
              m.map((msg) =>
                msg.id === assistantMsgId
                  ? {
                      ...msg,
                      text: assistantText,
                    }
                  : msg
              )
            );

            continue;
          }

          /* ───────────── GENERATED FILE EVENT ───────────── */

          if (event.type === "file") {
            const generatedFile =
              event.file || event.data || event;

            if (
              generatedFile &&
              generatedFile.id &&
              generatedFile.name
            ) {
              generatedFilesReceivedRef.current += 1;

              /*
               * A generated file is successful output.
               */
              streamSucceededRef.current = true;

              setMessages((m) =>
                m.map((msg) =>
                  msg.id === assistantMsgId
                    ? {
                        ...msg,
                        generatedFiles: [
                          ...(msg.generatedFiles || []),
                          generatedFile,
                        ],
                      }
                    : msg
                )
              );
            }

            setStatus("");
            continue;
          }

          /* ───────────── ERROR EVENT ───────────── */

          if (event.type === "error") {
            const errorMessage =
              event.message || "Assistant error";

            /*
             * Sometimes the backend can finish producing the useful
             * response/file and then emit a late timeout/error while
             * closing the stream.
             *
             * If we already have usable output, do NOT turn that into
             * a frontend failure.
             */
            if (
              streamSucceededRef.current ||
              assistantText.trim().length > 0 ||
              generatedFilesReceivedRef.current > 0
            ) {
              /*
               * This is intentionally not console.error.
               * A late backend stream error after successful output
               * is not a frontend authentication failure.
               */
              setStatus("");
              continue;
            }

            throw new Error(errorMessage);
          }

          /* Done */
          if (event.type === "done") {
            streamSucceededRef.current =
              streamSucceededRef.current ||
              assistantText.trim().length > 0 ||
              generatedFilesReceivedRef.current > 0;

            setStatus("");
            continue;
          }
        }
      }

      /*
       * Process a final SSE event if the server closed the stream
       * without a trailing blank line.
       */
      if (buffer.trim().startsWith("data: ")) {
        const line = buffer.trim();

        try {
          const event = JSON.parse(line.slice(6));

          if (event.type === "conversation") {
            if (event.conversation_id) {
              setConversationId(event.conversation_id);
            }
          }

          if (
            event.type === "token" ||
            event.type === "content" ||
            event.type === "delta"
          ) {
            const chunk =
              event.content ||
              event.delta ||
              event.text ||
              "";

            if (chunk) {
              assistantText += chunk;
              streamSucceededRef.current = true;

              setMessages((m) =>
                m.map((msg) =>
                  msg.id === assistantMsgId
                    ? {
                        ...msg,
                        text: assistantText,
                      }
                    : msg
                )
              );
            }
          }

          if (
            event.type === "message" &&
            event.role === "assistant"
          ) {
            const content = event.content || "";

            if (content) {
              assistantText = content;
              streamSucceededRef.current = true;
            }

            setMessages((m) =>
              m.map((msg) =>
                msg.id === assistantMsgId
                  ? {
                      ...msg,
                      text: assistantText,
                    }
                  : msg
              )
            );
          }

          if (event.type === "file") {
            const generatedFile =
              event.file || event.data || event;

            if (
              generatedFile &&
              generatedFile.id &&
              generatedFile.name
            ) {
              generatedFilesReceivedRef.current += 1;
              streamSucceededRef.current = true;

              setMessages((m) =>
                m.map((msg) =>
                  msg.id === assistantMsgId
                    ? {
                        ...msg,
                        generatedFiles: [
                          ...(msg.generatedFiles || []),
                          generatedFile,
                        ],
                      }
                    : msg
                )
              );
            }
          }

          if (event.type === "done") {
            streamSucceededRef.current =
              streamSucceededRef.current ||
              assistantText.trim().length > 0 ||
              generatedFilesReceivedRef.current > 0;

            setStatus("");
          }

          if (event.type === "error") {
            const errorMessage =
              event.message || "Assistant error";

            /*
             * Ignore a late error when the assistant already returned
             * useful text or a generated file.
             */
            if (
              streamSucceededRef.current ||
              assistantText.trim().length > 0 ||
              generatedFilesReceivedRef.current > 0
            ) {
              setStatus("");
            } else {
              throw new Error(errorMessage);
            }
          }
        } catch (err) {
          /*
           * Only surface a final SSE parsing/backend error if we did
           * not already receive successful assistant output.
           */
          if (
            !streamSucceededRef.current &&
            assistantText.trim().length === 0 &&
            generatedFilesReceivedRef.current === 0
          ) {
            throw err;
          }

          /*
           * Successful output already exists, so don't turn a
           * stream-closing issue into a visible frontend failure.
           */
          setStatus("");
        }
      }

      /*
       * Mark successful output one final time after the stream ends.
       */
      streamSucceededRef.current =
        streamSucceededRef.current ||
        assistantText.trim().length > 0 ||
        generatedFilesReceivedRef.current > 0;

      // Fallback if nothing was streamed
      if (
        !assistantText &&
        generatedFilesReceivedRef.current === 0
      ) {
        setMessages((m) =>
          m.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  text: "No response received from the assistant.",
                }
              : msg
          )
        );
      }
    } catch (err: any) {
      /*
       * A real session-expiration case is handled cleanly.
       *
       * Do not print the raw authentication error to the console.
       */
      if (err?.message === "SESSION_EXPIRED") {
        setMessages((m) => [
          ...m,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            text: "Your session has expired. Please sign in again.",
          },
        ]);

        return;
      }

      /*
       * Genuine assistant/backend failure.
       */
      console.error("Assistant request failed:", err);

      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: `Something went wrong: ${
            err?.message || "Please try again."
          }`,
        },
      ]);
    } finally {
      setBusy(false);
      setStatus("");
    }
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
        if (
          !e.currentTarget.contains(
            e.relatedTarget as Node
          )
        ) {
          setDragging(false);
        }
      }}
      onDrop={onDrop}
      className="relative overflow-hidden rounded-2xl border border-zinc-800/80 bg-zinc-950/80 shadow-[0_0_0_1px_rgba(255,255,255,0.03),0_20px_50px_-20px_rgba(0,0,0,0.7)] backdrop-blur"
    >
      {/* Top glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-sky-400/40 to-transparent"
      />

      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800/70 px-4 py-3.5 sm:px-5">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-sky-500/15 text-sky-400 ring-1 ring-sky-400/25">
            <svg
              viewBox="0 0 24 24"
              className="h-4.5 w-4.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z" />
              <path d="M19 16l.7 1.8L21.5 18.5l-1.8.7L19 21l-.7-1.8-1.8-.7 1.8-.7L19 16z" />
            </svg>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-zinc-100">
              NFL Edge AI
            </h2>

            <p className="text-xs text-zinc-500">
              Trends · Props · Insights
            </p>
          </div>
        </div>

        <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Ready
        </span>
      </div>

      {/* Conversation */}
      <div
        ref={scrollRef}
        className="h-[460px] overflow-y-auto px-4 py-5 sm:h-[520px] sm:px-5 lg:h-[560px]"
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <div className="flex h-full flex-col justify-end">
            <p className="mb-3.5 text-sm text-zinc-400">
              Start with a question or try one of these:
            </p>

            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-zinc-700/80 bg-zinc-900/70 px-3.5 py-2 text-left text-[13px] text-zinc-300 transition hover:border-sky-500/50 hover:bg-sky-500/10 hover:text-sky-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-400"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <ul className="space-y-4">
            {messages.map((m) => (
              <li
                key={m.id}
                className={
                  m.role === "user"
                    ? "flex justify-end"
                    : "flex justify-start"
                }
              >
                <div
                  className={
                    m.role === "user"
                      ? "max-w-[85%] rounded-2xl rounded-br-md bg-sky-600 px-4 py-2.5 text-sm text-white shadow-sm"
                      : "max-w-[85%] rounded-2xl rounded-bl-md border border-zinc-700/80 bg-zinc-900/80 px-4 py-2.5 text-sm text-zinc-200"
                  }
                >
                  {/* User attached files */}
                  {m.files && m.files.length > 0 && (
                    <div className="mb-1.5 flex flex-wrap gap-1.5">
                      {m.files.map((f) => (
                        <span
                          key={f}
                          className={`rounded-md px-2 py-0.5 text-xs ${
                            m.role === "user"
                              ? "bg-sky-700/60 text-sky-100"
                              : "bg-zinc-800 text-zinc-400"
                          }`}
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Assistant text */}
                  {m.text && (
                    <p className="whitespace-pre-wrap leading-relaxed">
                      {m.text}
                    </p>
                  )}

                  {/* Generated files */}
                  {m.role === "assistant" &&
                    m.generatedFiles &&
                    m.generatedFiles.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {m.generatedFiles.map((file) => {
                          const type = fileType(file);
                          const size = fmtSize(file.size_bytes);

                          const isDownloading =
                            downloadingFileId === file.id;

                          return (
                            <div
                              key={file.id}
                              className="flex items-center gap-3 rounded-xl border border-zinc-700/80 bg-zinc-950/80 p-3 shadow-sm"
                            >
                              {/* File icon */}
                              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-sky-500/10 text-sky-400 ring-1 ring-sky-400/20">
                                <svg
                                  viewBox="0 0 24 24"
                                  className="h-5 w-5"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth="1.7"
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                >
                                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                  <path d="M14 2v6h6" />
                                  <path d="M8 13h8" />
                                  <path d="M8 17h5" />
                                </svg>
                              </div>

                              {/* File info */}
                              <div className="min-w-0 flex-1">
                                <p
                                  className="truncate text-sm font-medium text-zinc-100"
                                  title={file.name}
                                >
                                  {file.name}
                                </p>

                                <p className="mt-0.5 text-[11px] text-zinc-500">
                                  {type}
                                  {size ? ` · ${size}` : ""}
                                </p>
                              </div>

                              {/* Download button */}
                              <button
                                type="button"
                                onClick={() =>
                                  downloadGeneratedFile(file)
                                }
                                disabled={Boolean(
                                  downloadingFileId
                                )}
                                className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-sky-500 px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
                              >
                                {isDownloading ? (
                                  <>
                                    <svg
                                      className="h-3.5 w-3.5 animate-spin"
                                      viewBox="0 0 24 24"
                                      fill="none"
                                    >
                                      <circle
                                        cx="12"
                                        cy="12"
                                        r="9"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                        className="opacity-30"
                                      />

                                      <path
                                        d="M21 12a9 9 0 0 0-9-9"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                        strokeLinecap="round"
                                      />
                                    </svg>

                                    Downloading…
                                  </>
                                ) : (
                                  <>
                                    <svg
                                      viewBox="0 0 24 24"
                                      className="h-3.5 w-3.5"
                                      fill="none"
                                      stroke="currentColor"
                                      strokeWidth="2"
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                    >
                                      <path d="M12 3v12" />
                                      <path d="M7 10l5 5 5-5" />
                                      <path d="M5 21h14" />
                                    </svg>

                                    Download
                                  </>
                                )}
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                </div>
              </li>
            ))}

            {/* Busy indicator */}
            {busy && (
              <li
                className="flex justify-start"
                aria-label="Assistant is working"
              >
                <div className="flex items-center gap-3 rounded-2xl rounded-bl-md border border-zinc-700/80 bg-zinc-900/80 px-4 py-3">
                  <div className="flex gap-1">
                    {[0, 150, 300].map((d) => (
                      <span
                        key={d}
                        className="h-1.5 w-1.5 animate-bounce rounded-full bg-sky-400"
                        style={{
                          animationDelay: `${d}ms`,
                        }}
                      />
                    ))}
                  </div>

                  <span className="text-sm text-sky-300/90">
                    {status || "Working…"}
                  </span>
                </div>
              </li>
            )}
          </ul>
        )}
      </div>

      {/* Composer */}
      <div className="border-t border-zinc-800/70 p-3 sm:p-4">
        {files.length > 0 && (
          <ul className="mb-2.5 flex flex-wrap gap-2">
            {files.map((f, idx) => (
              <li
                key={f.name + idx}
                className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-900 py-1.5 pl-2.5 pr-1 text-xs text-zinc-300"
              >
                <span className="max-w-[150px] truncate">
                  {f.name}
                </span>

                <span className="text-zinc-500">
                  {fmtSize(f.size)}
                </span>

                <button
                  type="button"
                  onClick={() =>
                    setFiles((p) =>
                      p.filter((_, j) => j !== idx)
                    )
                  }
                  aria-label={`Remove ${f.name}`}
                  className="grid h-5 w-5 place-items-center rounded-md text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-200"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="flex items-end gap-2 rounded-xl border border-zinc-700/80 bg-zinc-900/70 p-2 transition focus-within:border-sky-500/50 focus-within:ring-4 focus-within:ring-sky-500/10">
          <input
            ref={fileRef}
            type="file"
            multiple
            hidden
            onChange={(e) => {
              addFiles(e.target.files);
              e.target.value = "";
            }}
          />

          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            aria-label="Attach files"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-zinc-400 transition hover:bg-zinc-800 hover:text-sky-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-400"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-[18px] w-[18px]"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
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
            className="max-h-40 min-h-9 flex-1 resize-none bg-transparent py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
          />

          <button
            type="button"
            onClick={() => send()}
            disabled={
              busy ||
              (!input.trim() && files.length === 0)
            }
            aria-label="Send message"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-sky-500 text-white transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-zinc-700 disabled:text-zinc-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </div>

        <p className="mt-2 px-1 text-[11px] text-zinc-500">
          Enter to send · Shift+Enter for new line
        </p>
      </div>

      {/* Drop overlay */}
      {dragging && (
        <div className="absolute inset-0 z-10 grid place-items-center bg-zinc-950/90 backdrop-blur-sm">
          <div className="rounded-xl border border-dashed border-sky-400/60 px-8 py-6 text-center">
            <p className="text-sm font-medium text-sky-300">
              Drop files to attach
            </p>

            <p className="mt-1 text-xs text-zinc-500">
              Slips, screenshots, CSVs, PDFs
            </p>
          </div>
        </div>
      )}
    </section>
  );
}