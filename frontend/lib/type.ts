// lib/types.ts

export type Book = "draftkings" | "fanduel" | "betmgm" | "caesars" | string;

export interface Team {
  id: string;
  name: string;
  abbreviation: string;
  logo?: string;
}

export interface Odds {
  book: Book;
  spread?: number; // e.g. -3.5
  spreadPrice?: number; // American odds, e.g. -110
  total?: number; // e.g. 47.5
  totalOverPrice?: number;
  totalUnderPrice?: number;
  moneylineHome?: number;
  moneylineAway?: number;
  updatedAt: string; // ISO
}

export interface LinePoint {
  time: string; // ISO
  value: number;
}

export interface LineSeries {
  book: Book;
  points: LinePoint[];
}

export interface Injury {
  player: string;
  team: string;
  status: "Out" | "Doubtful" | "Questionable" | "Probable" | string;
  description?: string;
  reportedAt: string; // ISO - used for amber marker on chart
}

export interface Game {
  id: string;
  week: number;
  season: number;
  status: "scheduled" | "live" | "final" | string;
  kickoff: string; // ISO
  venue?: string | null;
  home: Team;
  away: Team;
  score?: {
    home: number;
    away: number;
  };
  // current consensus / best lines (for quick table display)
  spread?: number;
  total?: number;
  moneylineHome?: number;
  moneylineAway?: number;
  // movement
  spreadOpen?: number;
  totalOpen?: number;
  spreadMove?: number; // positive = moved toward home, etc.
  totalMove?: number;
  // best prices across books (for green highlight)
  bestSpread?: { book: Book; value: number; price: number };
  bestTotal?: { book: Book; value: number; price: number };
  bestMoneylineHome?: { book: Book; price: number };
  bestMoneylineAway?: { book: Book; price: number };
  // tiny sparkline data (last N points of spread or total)
  sparkline?: number[];
  // all books for this game (optional, can be fetched separately)
  odds?: Odds[];
}

export interface BiggestMove {
  gameId: string;
  matchup: string; // "KC @ BUF"
  market: "spread" | "total" | "moneyline";
  direction: "up" | "down";
  amount: number;
  book?: Book;
}

export interface GamesResponse {
  games: Game[];
  week: number;
  liveCount: number;
  stats: {
    gamesThisWeek: number;
    liveNow: number;
    biggestMove: number;
    averageTotal: number;
  };
  biggestMoves: BiggestMove[];
}

export interface LineHistoryResponse {
  gameId: string;
  market: "spread" | "total";
  series: LineSeries[];
  open: number;
  injuries: Injury[];
}