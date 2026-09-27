export type DataSourceStatus = 'live' | 'demo' | 'unavailable';

export interface DataSourcesMeta {
  nflGames: DataSourceStatus;
  odds: DataSourceStatus;
  injuries: DataSourceStatus;
  aiAnalysis: DataSourceStatus;
  lastUpdated: string;
}

export interface Team {
  id: string;
  name: string;
  abbreviation: string;
}

export interface MarketLine {
  opening: number | null;
  current: number | null;
  movement: number | null;
}

export interface Moneyline {
  opening: number | null;
  current: number | null;
  movement: number | null;
}

export interface GameSnapshot {
  id: string;
  startTime: string;
  status: string;
  homeTeam: Team;
  awayTeam: Team;
  spread: MarketLine;
  total: MarketLine;
  moneylineHome: Moneyline;
  moneylineAway: Moneyline;
  hasSignificantMovement: boolean;
  dataSource: DataSourceStatus;
}