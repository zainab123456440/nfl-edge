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

/* ───────────── Types & constants ───────────── */

type GeneratedFile = {
  id: string;
  name: string;
  mime_type?: string;
  size_bytes?: number;
  is_generated?: boolean;
  created_at?: string;
};

type ErrorInfo = {
  title: string;
  detail?: string;
  code?: string;
  retryable: boolean;
  retryText?: string;
};

type Msg = {
  id: string;
  role: "user" | "assistant";
  text: string;
  files?: string[];
  generatedFiles?: GeneratedFile[];
  error?: ErrorInfo;
  notice?: string;
};

const SUGGESTIONS = [
  "Which props have the biggest line movement today?",
  "Summarize key injuries for tonight's games",
  "Find hot trends over the last 10 games",
  "Break down the slip I upload",
];

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "https://nfl-backend-eight.vercel.app";

const STORAGE_BUCKET = "assistant-files";
const MAX_FILES = 10;

/* ───────────── Error handling ───────────── */

type ErrorKind = "session" | "network" | "timeout" | "http" | "stream";

const CONNECT_TIMEOUT_MS = 45000;
const STALL_TIMEOUT_MS = 90000;
const DOWNLOAD_TIMEOUT_MS = 30000;

class AssistantError extends Error {
  kind: ErrorKind;
  status?: number;
  detail?: string;
  code?: string;

  constructor(
    kind: ErrorKind,
    opts: { status?: number; statusText?: string; detail?: string } = {}
  ) {
    const code = opts.status
      ? `HTTP ${opts.status}${opts.statusText ? " " + opts.statusText : ""}`
      : undefined;

    super(
      [code ? `Request failed (${code})` : "", opts.detail]
        .filter(Boolean)
        .join(": ") ||
        (kind === "session"
          ? "Session expired"
          : kind === "network"
          ? "Network error"
          : kind === "timeout"
          ? "Request timed out"
          : "Assistant error")
    );

    this.name = "AssistantError";
    this.kind = kind;
    this.status = opts.status;
    this.detail = opts.detail;
    this.code = code;
  }
}

function stringifyError(value: unknown, fallback = "Unknown error"): string {
  if (value == null) return fallback;
  if (typeof value === "string") return value.trim() || fallback;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (value instanceof Error) return value.message || fallback;

  if (Array.isArray(value)) {
    const parts = value.map((v) => stringifyError(v, "")).filter(Boolean);
    return parts.length ? parts.join("; ") : fallback;
  }

  if (typeof value === "object") {
    const o = value as Record<string, unknown>;

    if (typeof o.msg === "string") {
      const loc = Array.isArray(o.loc)
        ? o.loc.filter((p) => p !== "body").join(".")
        : "";

      return loc ? `${loc}: ${o.msg}` : o.msg;
    }

    for (const key of [
      "detail",
      "message",
      "error",
      "errors",
      "error_description",
    ]) {
      if (o[key] != null) {
        const nested = stringifyError(o[key], "");
        if (nested) return nested;
      }
    }

    try {
      const json = JSON.stringify(value);
      return json && json !== "{}" ? json : fallback;
    } catch {
      return fallback;
    }
  }

  return fallback;
}

function statusTitle(status?: number): string {
  if (!status) return "Request failed";

  switch (status) {
    case 400:
      return "Invalid request";
    case 401:
      return "Not authorized";
    case 403:
      return "Access denied";
    case 404:
      return "Not found";
    case 408:
    case 504:
      return "The request timed out";
    case 413:
      return "File too large";
    case 422:
      return "Couldn't process that request";
    case 429:
      return "Too many requests";
    case 502:
    case 503:
      return "Service unavailable";
  }

  if (status >= 500) return "Server error";
  if (status >= 400) return "Request failed";
  return "Request failed";
}

function isRetryableStatus(status?: number): boolean {
  if (!status) return true;
  return status >= 500 || status === 408 || status === 429;
}

async function errorFromResponse(res: Response): Promise<AssistantError> {
  let detail = "";

  try {
    const raw = await res.text();

    if (raw) {
      try {
        detail = stringifyError(JSON.parse(raw), "");
      } catch {
        const looksLikeHtml = /^\s*<(!doctype|html)/i.test(raw);
        detail = looksLikeHtml ? "" : raw.trim().slice(0, 300);
      }
    }
  } catch {
    /* ignore */
  }

  return new AssistantError("http", {
    status: res.status,
    statusText: res.statusText,
    detail: detail || undefined,
  });
}

function toErrorInfo(err: unknown): ErrorInfo {
  if (err instanceof AssistantError) {
    switch (err.kind) {
      case "session":
        return {
          title: "Your session has expired",
          detail: "Please sign in again to continue.",
          retryable: false,
        };
      case "network":
        return {
          title: "Can't reach the server",
          detail: err.detail || "Check your connection and try again.",
          retryable: true,
        };
      case "timeout":
        return {
          title: "The request timed out",
          detail:
            err.detail ||
            "The server took too long to respond. Please try again.",
          retryable: true,
        };
      case "http":
        return {
          title: statusTitle(err.status),
          detail: err.detail,
          code: err.code,
          retryable: isRetryableStatus(err.status),
        };
      case "stream":
        return {
          title: "The assistant hit a problem",
          detail: err.detail,
          retryable: true,
        };
    }
  }

  return {
    title: "Something went wrong",
    detail: stringifyError(err, "Please try again."),
    retryable: true,
  };
}

/* ───────────── Authentication helpers ───────────── */

async function getAuthHeaders(): Promise<Record<string, string>> {
  const token = await getValidAccessToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

function authLookupError(err: unknown): Error {
  if (err instanceof AssistantError) return err;
  if ((err as any)?.name === "AbortError") return err as Error;

  console.error("Auth token lookup failed:", err);

  return new AssistantError("network", {
    detail:
      "Couldn't verify your sign-in. Check your connection and try again.",
  });
}

async function authenticatedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const doFetch = async (headers: Record<string, string>) => {
    try {
      return await fetch(url, {
        ...options,
        headers: {
          ...headers,
          ...((options.headers as Record<string, string>) || {}),
        },
      });
    } catch (err) {
      if ((err as any)?.name === "AbortError") throw err;

      const offline =
        typeof navigator !== "undefined" && navigator.onLine === false;

      throw new AssistantError("network", {
        detail: offline
          ? "You appear to be offline. Reconnect and try again."
          : err instanceof Error && err.message
          ? `${err.message}. Check your connection and try again.`
          : undefined,
      });
    }
  };

  let headers: Record<string, string>;

  try {
    headers = await getAuthHeaders();
  } catch (err) {
    throw authLookupError(err);
  }

  let response = await doFetch(headers);

  if (response.status === 401) {
    let refreshedToken: string | null | undefined;

    try {
      refreshedToken = await refreshAccessToken();
    } catch (err) {
      throw authLookupError(err);
    }

    if (!refreshedToken) {
      throw new AssistantError("session");
    }

    headers = {
      ...headers,
      Authorization: `Bearer ${refreshedToken}`,
    };

    response = await doFetch(headers);

    if (response.status === 401) {
      throw new AssistantError("session");
    }
  }

  return response;
}

/* ───────────── File upload helpers ───────────── */

function getUserIdFromToken(token: string): string {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.sub || payload.user_id || payload.id || "";
  } catch {
    return "";
  }
}

function safeFileName(name: string): string {
  return (name || "file").replace(/[^\w.\-]+/g, "_").slice(0, 120) || "file";
}

async function uploadAndRegisterFile(
  file: File,
  conversationId: string | null,
  signal?: AbortSignal
): Promise<string> {
  const token = await getValidAccessToken();
  if (!token) {
    throw new AssistantError("session");
  }

  const userId = getUserIdFromToken(token);
  if (!userId) {
    throw new AssistantError("session", {
      detail: "Could not identify the signed-in user.",
    });
  }

  const supabaseModule = "@supabase/supabase-js";
  const { createClient } = await import(supabaseModule);

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      global: {
        headers: { Authorization: `Bearer ${token}` },
      },
    }
  );

  const path = `${userId}/${crypto.randomUUID()}_${safeFileName(file.name)}`;

  const { error: storageError } = await supabase.storage
    .from(STORAGE_BUCKET)
    .upload(path, file, {
      contentType: file.type || "application/octet-stream",
      upsert: true,
    });

  if (storageError) {
    throw new AssistantError("stream", {
      detail: `Upload failed for ${file.name}: ${storageError.message}`,
    });
  }

  const registerRes = await authenticatedFetch(`${API_BASE}/assistant/files`, {
    method: "POST",
    signal,
    body: JSON.stringify({
      storage_path: path,
      name: file.name,
      mime_type: file.type || "application/octet-stream",
      size_bytes: file.size,
      conversation_id: conversationId || undefined,
    }),
  });

  if (!registerRes.ok) {
    try {
      await supabase.storage.from(STORAGE_BUCKET).remove([path]);
    } catch {
      /* ignore */
    }
    throw await errorFromResponse(registerRes);
  }

  const data = await registerRes.json();

  if (!data?.id) {
    throw new AssistantError("stream", {
      detail: `Server did not return a file id for ${file.name}`,
    });
  }

  return data.id as string;
}

/* ───────────── Formatting helpers ───────────── */

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

/* ───────────── Error card ───────────── */

function ErrorCard({
  error,
  disabled,
  onRetry,
}: {
  error: ErrorInfo;
  disabled: boolean;
  onRetry?: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const copyDetails = async () => {
    const report = [error.title, error.code, error.detail]
      .filter(Boolean)
      .join("\n");

    try {
      await navigator.clipboard.writeText(report);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* ignore */
    }
  };

  return (
    <div role="alert" className="flex items-start gap-3">
      <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-red-500/10 text-red-400 ring-1 ring-red-400/25">
        <svg
          viewBox="0 0 24 24"
          className="h-4 w-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.9"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 9v4" />
          <path d="M12 17h.01" />
          <path d="M10.3 3.9L2.4 17.5A2 2 0 0 0 4.1 20.5h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
        </svg>
      </div>

      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-red-200">{error.title}</p>

        {error.detail && (
          <p className="mt-1 max-h-32 overflow-y-auto whitespace-pre-wrap break-words text-[13px] leading-relaxed text-zinc-300">
            {error.detail}
          </p>
        )}

        {error.code && (
          <span className="mt-2 inline-block rounded-md bg-zinc-800/80 px-2 py-0.5 font-mono text-[11px] text-zinc-400">
            {error.code}
          </span>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {error.retryable && onRetry && (
            <button
              type="button"
              onClick={onRetry}
              disabled={disabled}
              className="inline-flex items-center gap-1.5 rounded-lg bg-sky-500 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
            >
              <svg
                viewBox="0 0 24 24"
                className="h-3.5 w-3.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M3 12a9 9 0 0 1 15.5-6.2L21 8" />
                <path d="M21 3v5h-5" />
                <path d="M21 12a9 9 0 0 1-15.5 6.2L3 16" />
                <path d="M3 21v-5h5" />
              </svg>
              Try again
            </button>
          )}

          {(error.detail || error.code) && (
            <button
              type="button"
              onClick={copyDetails}
              className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:bg-zinc-800 hover:text-zinc-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-400"
            >
              {copied ? "Copied" : "Copy details"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ───────────── Assistant ───────────── */

export function AIAssistant() {
  // Always start fresh – no history is loaded
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

  const streamSucceededRef = useRef(false);
  const generatedFilesReceivedRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

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
    setFiles((prev) => [...prev, ...Array.from(list)].slice(0, MAX_FILES));
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const pushError = (error: ErrorInfo) => {
    setMessages((m) => [
      ...m,
      {
        id: crypto.randomUUID(),
        role: "assistant",
        text: "",
        error,
      },
    ]);
  };

  /* ───────────── Generated file download ───────────── */

  const downloadGeneratedFile = async (file: GeneratedFile) => {
    if (!file.id || downloadingFileId) return;

    setDownloadingFileId(file.id);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), DOWNLOAD_TIMEOUT_MS);

    try {
      const res = await authenticatedFetch(
        `${API_BASE}/assistant/files/${encodeURIComponent(file.id)}/download`,
        {
          method: "GET",
          signal: controller.signal,
        }
      );

      if (!res.ok) throw await errorFromResponse(res);

      const data = await res.json().catch(() => null);

      if (!data?.url) {
        throw new AssistantError("stream", {
          detail: "The server did not return a download URL.",
        });
      }

      const anchor = document.createElement("a");
      anchor.href = data.url;
      anchor.download = file.name || "download";
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    } catch (err) {
      console.error("File download failed:", err);

      const failure: unknown =
        (err as any)?.name === "AbortError"
          ? new AssistantError("timeout", {
              detail: "The download took too long to start.",
            })
          : err;

      const info = toErrorInfo(failure);

      pushError({
        ...info,
        title:
          failure instanceof AssistantError && failure.kind === "session"
            ? info.title
            : `Couldn't download ${file.name || "the file"}`,
        retryable: false,
      });
    } finally {
      clearTimeout(timer);
      setDownloadingFileId(null);
    }
  };

  /* ───────────── Send ───────────── */

  const send = async (override?: string, isRetry = false) => {
    const text = (override ?? input).trim();

    if ((!text && files.length === 0) || busy) return;

    streamSucceededRef.current = false;
    generatedFilesReceivedRef.current = 0;

    const sentFiles = isRetry ? [] : [...files];

    let assistantMsgId: string | null = null;
    let assistantText = "";

    const controller = new AbortController();
    abortRef.current = controller;

    const state = {
      timedOutReason: null as string | null,
      sawDone: false,
      interrupted: false,
    };

    let timer: ReturnType<typeof setTimeout> | undefined;

    const armTimer = (ms: number, reason: string) => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        state.timedOutReason = reason;
        controller.abort();
      }, ms);
    };

    if (!isRetry) {
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "user",
          text,
          files: sentFiles.map((f) => f.name),
        },
      ]);

      setInput("");
      setFiles([]);
    }

    setBusy(true);
    setStatus("Thinking…");

    const hasOutput = () =>
      streamSucceededRef.current ||
      assistantText.trim().length > 0 ||
      generatedFilesReceivedRef.current > 0;

    const updateAssistant = (patch: (msg: Msg) => Msg) => {
      const id = assistantMsgId;
      if (!id) return;
      setMessages((m) => m.map((msg) => (msg.id === id ? patch(msg) : msg)));
    };

    const handleEvent = (event: any) => {
      if (!event || typeof event !== "object") return;

      if (event.type === "conversation") {
        if (event.conversation_id) {
          setConversationId(event.conversation_id);
        }
        return;
      }

      if (event.type === "status" || event.type === "thinking") {
        setStatus(
          stringifyError(event.message ?? event.content, "Working…")
        );
        return;
      }

      if (
        event.type === "token" ||
        event.type === "content" ||
        event.type === "delta"
      ) {
        const chunk = event.content || event.delta || event.text || "";

        if (typeof chunk === "string" && chunk) {
          assistantText += chunk;
          streamSucceededRef.current = true;
          const snapshot = assistantText;
          updateAssistant((msg) => ({ ...msg, text: snapshot }));
        }

        setStatus("");
        return;
      }

      if (event.type === "message" && event.role === "assistant") {
        const content = event.content || "";

        if (typeof content === "string" && content) {
          assistantText = content;
          streamSucceededRef.current = true;
        }

        const snapshot = assistantText;
        updateAssistant((msg) => ({ ...msg, text: snapshot }));
        return;
      }

      if (event.type === "file") {
        const generatedFile = event.file || event.data || event;

        if (generatedFile && generatedFile.id && generatedFile.name) {
          generatedFilesReceivedRef.current += 1;
          streamSucceededRef.current = true;

          updateAssistant((msg) => ({
            ...msg,
            generatedFiles: [...(msg.generatedFiles || []), generatedFile],
          }));
        }

        setStatus("");
        return;
      }

      if (event.type === "error") {
        const detail = stringifyError(
          event.message ?? event.detail ?? event.error,
          "Assistant error"
        );

        if (hasOutput()) {
          console.warn("Ignoring late stream error after output:", detail);
          state.interrupted = true;
          setStatus("");
          return;
        }

        throw new AssistantError("stream", { detail });
      }

      if (event.type === "done") {
        state.sawDone = true;
        streamSucceededRef.current = hasOutput();
        setStatus("");
      }
    };

    const processPart = (part: string) => {
      const data = part
        .split("\n")
        .map((l) => l.trim())
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trimStart())
        .join("\n");

      if (!data || data === "[DONE]") return;

      let event: any;

      try {
        event = JSON.parse(data);
      } catch {
        return;
      }

      handleEvent(event);
    };

    try {
      // -------------------------------------------------------
      // 1. Upload binaries to Storage + register via POST /assistant/files
      // -------------------------------------------------------
      const fileIds: string[] = [];

      if (sentFiles.length > 0) {
        setStatus(
          sentFiles.length === 1
            ? "Uploading file…"
            : `Uploading ${sentFiles.length} files…`
        );

        for (let i = 0; i < sentFiles.length; i++) {
          const file = sentFiles[i];

          setStatus(
            sentFiles.length === 1
              ? `Uploading ${file.name}…`
              : `Uploading ${i + 1}/${sentFiles.length}: ${file.name}`
          );

          const id = await uploadAndRegisterFile(
            file,
            conversationId,
            controller.signal
          );

          fileIds.push(id);
        }
      }

      // -------------------------------------------------------
      // 2. Call streaming chat endpoint
      // -------------------------------------------------------

      armTimer(CONNECT_TIMEOUT_MS, "The server took too long to respond.");

      const res = await authenticatedFetch(`${API_BASE}/assistant/chat`, {
        method: "POST",
        signal: controller.signal,
        body: JSON.stringify({
          message: text,
          file_ids: fileIds,
          conversation_id: conversationId,
        }),
      });

      if (!res.ok) throw await errorFromResponse(res);

      if (!res.body) {
        throw new AssistantError("stream", {
          detail: "The server sent an empty response.",
        });
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";
      const newId = crypto.randomUUID();
      assistantMsgId = newId;

      setMessages((m) => [
        ...m,
        {
          id: newId,
          role: "assistant",
          text: "",
          generatedFiles: [],
        },
      ]);

      try {
        while (true) {
          armTimer(STALL_TIMEOUT_MS, "The assistant stopped responding.");

          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            processPart(part);
          }
        }

        buffer += decoder.decode();
        if (buffer.trim()) {
          processPart(buffer);
        }
      } catch (streamErr) {
        if (streamErr instanceof AssistantError) throw streamErr;

        const aborted = (streamErr as any)?.name === "AbortError";

        if (hasOutput()) {
          console.warn("Stream interrupted after output:", streamErr);
          state.interrupted = true;
        } else if (aborted) {
          throw streamErr;
        } else {
          throw new AssistantError("network", {
            detail:
              "The connection was lost while waiting for the response.",
          });
        }
      }

      streamSucceededRef.current = hasOutput();

      if (!hasOutput()) {
        throw new AssistantError("stream", {
          detail: "The assistant finished without sending a response.",
        });
      }

      if (state.interrupted && !state.sawDone) {
        const why = state.timedOutReason
          ? "The assistant stopped responding"
          : "The connection was interrupted";

        updateAssistant((msg) => ({
          ...msg,
          notice: `${why}, so this response may be incomplete. Ask again to get the full answer.`,
        }));
      }
    } catch (err) {
      let failure: unknown = err;

      if ((err as any)?.name === "AbortError") {
        if (state.timedOutReason) {
          failure = new AssistantError("timeout", {
            detail: state.timedOutReason,
          });
        } else {
          return; // cancelled on purpose
        }
      }

      // -------------------------------------------------------
      // Silent auto-retry on context_length_exceeded
      // -------------------------------------------------------
      const detailText =
        failure instanceof AssistantError
          ? (failure.detail || failure.message || "").toLowerCase()
          : String(failure).toLowerCase();

      const isContextError =
        detailText.includes("context_length_exceeded") ||
        detailText.includes("context window") ||
        detailText.includes("input exceeds the context");

      if (isContextError && !isRetry) {
        console.warn(
          "Context length exceeded – automatically retrying without large files…"
        );
        // Retry once with the same text but without re-attaching files
        return send(text, true);
      }

      // -------------------------------------------------------
      // Normal error handling
      // -------------------------------------------------------
      console.error("Assistant request failed:", failure);

      const info = toErrorInfo(failure);
      const placeholderId = assistantMsgId;

      setMessages((m) => {
        const cleaned = m.filter(
          (msg) =>
            !(
              msg.id === placeholderId &&
              !msg.text &&
              !(msg.generatedFiles && msg.generatedFiles.length > 0)
            )
        );

        return [
          ...cleaned,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            text: "",
            error: {
              ...info,
              retryText: info.retryable ? text : undefined,
            },
          },
        ];
      });
    } finally {
      if (timer) clearTimeout(timer);
      if (abortRef.current === controller) abortRef.current = null;
      setBusy(false);
      setStatus("");
    }
  };

  const retry = (errorMsgId: string, retryText?: string) => {
    if (!retryText || busy) return;
    setMessages((m) => m.filter((msg) => msg.id !== errorMsgId));
    send(retryText, true);
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
        if (!e.currentTarget.contains(e.relatedTarget as Node)) {
          setDragging(false);
        }
      }}
      onDrop={onDrop}
      className="relative overflow-hidden rounded-2xl border border-zinc-800/80 bg-zinc-950/80 shadow-[0_0_0_1px_rgba(255,255,255,0.03),0_20px_50px_-20px_rgba(0,0,0,0.7)] backdrop-blur"
    >
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
            <p className="text-xs text-zinc-500">Trends · Props · Insights</p>
          </div>
        </div>

        <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Ready
        </span>
      </div>

      {/* Conversation – always starts empty */}
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
                  m.role === "user" ? "flex justify-end" : "flex justify-start"
                }
              >
                <div
                  className={
                    m.role === "user"
                      ? "max-w-[85%] rounded-2xl rounded-br-md bg-sky-600 px-4 py-2.5 text-sm text-white shadow-sm"
                      : m.error
                      ? "max-w-[85%] rounded-2xl rounded-bl-md border border-red-500/30 bg-red-500/[0.06] px-4 py-3 text-sm text-zinc-200"
                      : "max-w-[85%] rounded-2xl rounded-bl-md border border-zinc-700/80 bg-zinc-900/80 px-4 py-2.5 text-sm text-zinc-200"
                  }
                >
                  {m.error && (
                    <ErrorCard
                      error={m.error}
                      disabled={busy}
                      onRetry={
                        m.error.retryText
                          ? () => retry(m.id, m.error?.retryText)
                          : undefined
                      }
                    />
                  )}

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

                  {m.text && (
                    <p className="whitespace-pre-wrap leading-relaxed">
                      {m.text}
                    </p>
                  )}

                  {m.notice && (
                    <p
                      role="status"
                      className="mt-2.5 flex items-start gap-2 rounded-lg border border-amber-500/25 bg-amber-500/[0.07] px-2.5 py-2 text-xs leading-relaxed text-amber-200/90"
                    >
                      <span aria-hidden className="mt-px">
                        ⚠
                      </span>
                      <span>{m.notice}</span>
                    </p>
                  )}

                  {m.role === "assistant" &&
                    m.generatedFiles &&
                    m.generatedFiles.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {m.generatedFiles.map((file) => {
                          const type = fileType(file);
                          const size = fmtSize(file.size_bytes);
                          const isDownloading = downloadingFileId === file.id;

                          return (
                            <div
                              key={file.id}
                              className="flex items-center gap-3 rounded-xl border border-zinc-700/80 bg-zinc-950/80 p-3 shadow-sm"
                            >
                              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-sky-500/10 text-sky-400 ring-1 ring-sky-400/20">
                                <svg
                                  viewBox="0 0 24 24"
                                  className="h-5 w-5"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth="1.7"
                                  strokeLinejoin="round"
                                >
                                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                  <path d="M14 2v6h6" />
                                  <path d="M8 13h8" />
                                  <path d="M8 17h5" />
                                </svg>
                              </div>

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

                              <button
                                type="button"
                                onClick={() => downloadGeneratedFile(file)}
                                disabled={Boolean(downloadingFileId)}
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
                        style={{ animationDelay: `${d}ms` }}
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
                <span className="max-w-[150px] truncate">{f.name}</span>
                <span className="text-zinc-500">{fmtSize(f.size)}</span>
                <button
                  type="button"
                  onClick={() =>
                    setFiles((p) => p.filter((_, j) => j !== idx))
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
            disabled={busy || (!input.trim() && files.length === 0)}
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