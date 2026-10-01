// types/props.ts
export type Market = { key: string; label: string; sort_order?: number };

export type BookLine = {
  id?: number; // props_current.id, used for /props/{id}/history
  key: string;
  name?: string;
  line: number | null;
  over_odds: number | null;
  under_odds: number | null;
  line_movement?: number | null;
};

export type HitSummary = {
  games: number;
  over: number | null;
  under: number | null;
  push: number | null;
  over_pct: number | null;
  avg: number | null;
  window?: number;
  opponent?: string;
};

export type BoardRow = {
  player_id: number;
  player_name: string;
  team?: string;
  position?: string;
  market: string;
  market_label?: string;
  game_id: number;
  consensus_line: number | null;
  books: BookLine[];
  hit_rate: HitSummary | null;
};

export type HistoryPoint = { recorded_at: string; line: number; book: string };

export type RecentGame = {
  game_id: number;
  date: string;
  week: number;
  opponent: string | null;
  is_home: boolean | null;
  value: number;
  result: "over" | "under" | "push" | null;
};

export type HitRateResponse = {
  supported: boolean;
  reason?: string;
  games_available?: number;
  windows?: Record<string, HitSummary | null>;
};