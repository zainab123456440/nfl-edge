// lib/propsApi.ts
import type {
  BoardRow, HistoryPoint, HitRateResponse, Market, RecentGame,
} from "../types/props";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string, params: Record<string, unknown> = {}): Promise<T> {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
  });
  const res = await fetch(`${API}${path}${q.size ? `?${q}` : ""}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const getMarkets = async () => {
  const m = await get<Market[] | { data: Market[] }>("/props/markets");
  return Array.isArray(m) ? m : m.data;
};

// "DraftKings", "draft_kings", "draft-kings" -> "draftkings"
const normKey = (v: unknown) =>
  String(v ?? "").toLowerCase().replace(/[\s_-]/g, "");

// Find the per-book prices on a board row, whatever the backend calls them.
// Accepts an array, or an object keyed by book name ({ draftkings: {...} }).
function extractBooks(r: any): any[] {
  const candidates = [r.books, r.odds, r.offers, r.bookmakers, r.lines];

  for (const c of candidates) {
    if (Array.isArray(c) && c.length) {
      return c.map((b) => ({
        ...b,
        key: normKey(
          b.key ?? b.bookmaker_key ?? b.book ?? b.bookmaker ?? b.sportsbook ?? b.name
        ),
      }));
    }
    if (c && typeof c === "object" && !Array.isArray(c) && Object.keys(c).length) {
      return Object.entries(c).map(([k, b]: [string, any]) => ({
        ...b,
        key: normKey(b?.key ?? b?.bookmaker_key ?? k),
      }));
    }
  }
  return [];
}

export const getBoard = async (p: {
  week?: number; market?: string; position?: string; book?: string; search?: string;
}) => {
  const res = await get<{ count: number; data: any[] }>("/props/board", p);

  // DEBUG: shows the raw row from your backend. Remove when the books show up.
  if (typeof window !== "undefined") {
    console.log("RAW BOARD ROW:", JSON.stringify(res.data?.[0], null, 2));
  }

  return res.data.map(
    (r): BoardRow => ({ ...r, books: extractBooks(r), hit_rate: r.hit_rate ?? null })
  );
};

export const getHistory = async (propId: number) => {
  const res = await get<{ points: any[] }>(`/props/${propId}/history`);
  return res.points.map(
    (p): HistoryPoint => ({
      recorded_at: p.recorded_at,
      line: Number(p.line),
      book: p.bookmaker_key ?? p.book ?? String(p.bookmaker_id),
    })
  );
};

// ASSUMED routes for the stats service. Change the paths if your router differs.
export const getRecentGames = (r: BoardRow) =>
  get<{ supported: boolean; games: RecentGame[] }>("/props/recent-games", {
    player_id: r.player_id, market: r.market, line: r.consensus_line, limit: 10,
  });

export const getHitRate = (r: BoardRow) =>
  get<HitRateResponse>("/props/hit-rate", {
    player_id: r.player_id, market: r.market, line: r.consensus_line, game_id: r.game_id,
  });

export const fmtOdds = (n: number | null | undefined) =>
  n == null ? "–" : n > 0 ? `+${n}` : String(n);