// lib/api.ts

import type {
  GamesResponse,
  LineHistoryResponse,
  Game,
  Team,
  Odds,
  BiggestMove,
  LineSeries,
  Injury,
} from "./type";

import {
  getValidAccessToken,
  refreshAccessToken,
} from "../services/AuthAPI";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Authenticated fetcher
// ---------------------------------------------------------------------------

async function fetcher<T>(
  endpoint: string,
  init?: RequestInit
): Promise<T> {
  let hasRetriedAfterRefresh = false;

  while (true) {
    const token = await getValidAccessToken();

    const headers = new Headers(init?.headers);

    if (!headers.has("Content-Type")) {
      headers.set(
        "Content-Type",
        "application/json"
      );
    }

    if (
      token &&
      !headers.has("Authorization")
    ) {
      headers.set(
        "Authorization",
        `Bearer ${token}`
      );
    }

    let res: Response;

    try {
      res = await fetch(
        `${BASE_URL}${endpoint}`,
        {
          ...init,
          headers,
          cache: "no-store",
        }
      );
    } catch (error) {
      throw error;
    }

    // -----------------------------------------------------------------------
    // Successful response
    // -----------------------------------------------------------------------

    if (res.ok) {
      if (res.status === 204) {
        return undefined as T;
      }

      return res.json() as Promise<T>;
    }

    // -----------------------------------------------------------------------
    // Unauthorized
    //
    // The access token may have expired between token validation and the
    // actual request. Refresh once and retry the request.
    // -----------------------------------------------------------------------

    if (
      res.status === 401 &&
      !hasRetriedAfterRefresh
    ) {
      hasRetriedAfterRefresh = true;

      const freshToken =
        await refreshAccessToken();

      if (freshToken) {
        continue;
      }

      /*
       * Do not immediately delete authentication tokens here.
       *
       * AuthAPI owns token/session management. If the refresh token is
       * genuinely invalid, the auth layer can handle the expired session.
       */
      throw new Error(
        "Your session could not be refreshed."
      );
    }

    // -----------------------------------------------------------------------
    // Other backend errors
    // -----------------------------------------------------------------------

    const text =
      await res.text().catch(() => "");

    throw new Error(
      `API ${res.status}: ${
        text || res.statusText
      }`
    );
  }
}

/* ------------------------------------------------------------------ */
/* Backend (FastAPI) response shapes                                   */
/* ------------------------------------------------------------------ */

type Move = {
  open: number | null;
  current: number | null;
  change: number | null;
};

interface ApiTeam {
  id: number;
  name: string;
  abbreviation: string;
}

interface ApiBookOdds {
  spread?: {
    home?: {
      line: number;
      price: number;
    };
  };
  total?: {
    line?: number;
    over?: number;
    under?: number;
  };
  moneyline?: {
    home?: number;
    away?: number;
  };
  updated_at?: string | null;
}

interface ApiGame {
  id: number;
  season: number;
  week: number | null;
  kickoff_at: string;
  status: string;
  home_score: number | null;
  away_score: number | null;
  venue: string | null;
  home_team: ApiTeam | null;
  away_team: ApiTeam | null;
  odds: Record<string, ApiBookOdds>;
  movement: {
    spread_home: Move;
    total: Move;
  };
}

interface ApiGamesResponse {
  season: number;
  week: number | null;
  games: ApiGame[];
}

interface ApiLinePoint {
  t: string;
  line: number | null;
  price: number | null;
}

interface ApiLineHistory {
  series: Record<string, ApiLinePoint[]>;
}

interface ApiInjury {
  player_name: string;
  team_id: number;
  status: string;
  description: string | null;
  reported_at: string | null;
  captured_at: string | null;
}

/* ------------------------------------------------------------------ */
/* Adapters: backend shape -> frontend shape                           */
/* ------------------------------------------------------------------ */

const TBD: Team = {
  id: "0",
  name: "TBD",
  abbreviation: "TBD",
};

const toTeam = (
  t: ApiTeam | null
): Team =>
  t
    ? {
        id: String(t.id),
        name: t.name,
        abbreviation: t.abbreviation,
      }
    : TBD;

function normalizeStatus(
  raw: string
): "scheduled" | "live" | "final" {
  const s = (raw ?? "").toLowerCase();

  if (s.includes("final")) {
    return "final";
  }

  if (
    ["progress", "live", "half", "quarter"].some(
      (k) => s.includes(k)
    )
  ) {
    return "live";
  }

  return "scheduled";
}

function toGame(
  g: ApiGame
): Game {
  const status = normalizeStatus(
    g.status
  );

  const odds: Odds[] = Object.entries(
    g.odds ?? {}
  ).map(([book, o]) => ({
    book,
    spread:
      o.spread?.home?.line,
    spreadPrice:
      o.spread?.home?.price,
    total:
      o.total?.line,
    totalOverPrice:
      o.total?.over,
    totalUnderPrice:
      o.total?.under,
    moneylineHome:
      o.moneyline?.home,
    moneylineAway:
      o.moneyline?.away,
    updatedAt:
      o.updated_at ?? "",
  }));

  const ml = (
    k:
      | "moneylineHome"
      | "moneylineAway"
  ) =>
    odds.find(
      (o) => o[k] !== undefined
    )?.[k];

  const sp =
    g.movement?.spread_home;

  const tt =
    g.movement?.total;

  return {
    id: String(g.id),

    week:
      g.week ?? 0,

    season:
      g.season,

    status,

    kickoff:
      g.kickoff_at,

    venue:
      g.venue,

    home:
      toTeam(g.home_team),

    away:
      toTeam(g.away_team),

    score:
      status === "scheduled"
        ? undefined
        : {
            home:
              g.home_score ?? 0,
            away:
              g.away_score ?? 0,
          },

    spread:
      sp?.current ??
      undefined,

    spreadOpen:
      sp?.open ??
      undefined,

    spreadMove:
      sp?.change ??
      undefined,

    total:
      tt?.current ??
      undefined,

    totalOpen:
      tt?.open ??
      undefined,

    totalMove:
      tt?.change ??
      undefined,

    moneylineHome:
      ml("moneylineHome"),

    moneylineAway:
      ml("moneylineAway"),

    odds,
  };
}

/* ------------------------------------------------------------------ */
/* Games                                                               */
/* ------------------------------------------------------------------ */

/** Games list with optional filters (week, book, team search). */
export async function getGames(
  params?: {
    week?: number;
    book?: string;
    team?: string;
  }
): Promise<GamesResponse> {
  const search =
    new URLSearchParams();

  if (
    params?.week !== undefined
  ) {
    search.set(
      "week",
      String(params.week)
    );
  }

  if (params?.book) {
    search.set(
      "book",
      params.book
    );
  }

  if (params?.team) {
    search.set(
      "team",
      params.team
    );
  }

  const qs =
    search.toString();

  const raw =
    await fetcher<ApiGamesResponse>(
      `/games${
        qs ? `?${qs}` : ""
      }`
    );

  const games =
    (raw.games ?? []).map(
      toGame
    );

  const moves: BiggestMove[] =
    games
      .flatMap((g) => {
        const matchup =
          `${g.away.abbreviation} @ ${g.home.abbreviation}`;

        const out: BiggestMove[] =
          [];

        if (g.spreadMove) {
          out.push({
            gameId: g.id,
            matchup,
            market: "spread",
            direction:
              g.spreadMove > 0
                ? "up"
                : "down",
            amount:
              Math.abs(
                g.spreadMove
              ),
          });
        }

        if (g.totalMove) {
          out.push({
            gameId: g.id,
            matchup,
            market: "total",
            direction:
              g.totalMove > 0
                ? "up"
                : "down",
            amount:
              Math.abs(
                g.totalMove
              ),
          });
        }

        return out;
      })
      .sort(
        (a, b) =>
          b.amount - a.amount
      );

  const totals =
    games
      .map((g) => g.total)
      .filter(
        (t): t is number =>
          t !== undefined
      );

  const liveNow =
    games.filter(
      (g) =>
        g.status === "live"
    ).length;

  return {
    games,

    week:
      raw.week ?? 0,

    liveCount:
      liveNow,

    stats: {
      gamesThisWeek:
        games.length,

      liveNow,

      biggestMove:
        moves[0]?.amount ?? 0,

      averageTotal:
        totals.length
          ? Math.round(
              (
                totals.reduce(
                  (a, b) =>
                    a + b,
                  0
                ) /
                totals.length
              ) * 10
            ) / 10
          : 0,
    },

    biggestMoves:
      moves.slice(0, 5),
  };
}

/** Single game detail. */
export async function getGame(
  gameId: string
): Promise<Game> {
  const raw =
    await fetcher<ApiGame>(
      `/games/${gameId}`
    );

  return toGame(raw);
}

/** Line history + injuries for the slide-over chart. */
export async function getLineHistory(
  gameId: string,
  market:
    | "spread"
    | "total" = "spread",
  game?: Game
): Promise<LineHistoryResponse> {
  const apiMarket =
    market === "spread"
      ? "spreads"
      : "totals";

  const [
    hist,
    detail,
  ] = await Promise.all([
    fetcher<ApiLineHistory>(
      `/games/${gameId}/line-history?market=${apiMarket}`
    ),

    fetcher<{
      injuries: ApiInjury[];
    }>(
      `/games/${gameId}`
    ),
  ]);

  const series: LineSeries[] =
    Object.entries(
      hist.series ?? {}
    ).map(
      ([book, pts]) => ({
        book,

        points:
          pts
            .filter(
              (p) =>
                p.line !== null
            )
            .map((p) => ({
              time: p.t,
              value:
                p.line as number,
            })),
      })
    );

  const firstValue =
    series.find(
      (s) =>
        s.points.length
    )?.points[0]?.value;

  const open =
    (
      market === "spread"
        ? game?.spreadOpen
        : game?.totalOpen
    ) ??
    firstValue ??
    0;

  const abbr:
    Record<string, string> =
    {};

  if (game) {
    abbr[game.home.id] =
      game.home.abbreviation;

    abbr[game.away.id] =
      game.away.abbreviation;
  }

  const injuries: Injury[] =
    (
      detail.injuries ??
      []
    ).map((i) => ({
      player:
        i.player_name,

      team:
        abbr[
          String(i.team_id)
        ] ??
        String(i.team_id),

      status:
        i.status,

      description:
        i.description ??
        undefined,

      reportedAt:
        i.reported_at ??
        i.captured_at ??
        "",
    }));

  return {
    gameId,
    market,
    series,
    open,
    injuries,
  };
}

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

export interface PropHitRate {
  games: number;
  over: number;
  under: number;
  push: number;
  over_pct: number | null;
  avg: number | null;
  window?: number;
}

export interface PropRecentGame {
  game_id: number;
  date: string;
  opponent?: string | null;
  value: number;
  result?:
    | "over"
    | "under"
    | "push"
    | null;
}

export interface PropBoardRow {
  id: string | number;
  player_id: number;
  player_name?: string;
  team?: string;
  opponent?: string;
  game_id?: number;
  game?: string;
  market: string;
  line?: number | null;
  over_odds?: number | null;
  under_odds?: number | null;
  consensus_line?: number | null;
  hit_rate?: PropHitRate | null;
  recent_games?: PropRecentGame[];
}

export interface PropsBoardResponse {
  props: PropBoardRow[];
  [key: string]: unknown;
}

/** Player props board. */
export async function getPropsBoard(
  params?: {
    week?: number;
    market?: string;
    game?: string;
    player?: string;
  }
): Promise<PropsBoardResponse> {
  const search =
    new URLSearchParams();

  if (
    params?.week !== undefined
  ) {
    search.set(
      "week",
      String(params.week)
    );
  }

  if (params?.market) {
    search.set(
      "market",
      params.market
    );
  }

  if (params?.game) {
    search.set(
      "game",
      params.game
    );
  }

  if (params?.player) {
    search.set(
      "player",
      params.player
    );
  }

  const qs =
    search.toString();

  return fetcher<PropsBoardResponse>(
    `/props/board${
      qs ? `?${qs}` : ""
    }`
  );
}

/* ------------------------------------------------------------------ */
/* AI assistant                                                        */
/* ------------------------------------------------------------------ */

const AI_MOCK =
  process.env.NEXT_PUBLIC_AI_MOCK !==
  "false";

const wait = (
  ms: number
) =>
  new Promise((resolve) =>
    setTimeout(
      resolve,
      ms
    )
  );

export interface UploadedFileRef {
  id: string;
  name: string;
  size: number;
}

export interface GeneratedFile {
  id?: string;
  name: string;
  kind: string;
  mime: string;
  url?: string;
  content?: string;
}

export interface ChatReply {
  text: string;
  file?: GeneratedFile;
}

interface ApiChatResponse {
  reply: string;
  file?: GeneratedFile | null;
}

/**
 * Upload a user file.
 *
 * Uses getValidAccessToken() so an expired/near-expiry token
 * is refreshed before the multipart request.
 */
export async function uploadFile(
  file: File
): Promise<UploadedFileRef> {
  if (AI_MOCK) {
    await wait(300);

    return {
      id:
        crypto.randomUUID(),

      name:
        file.name,

      size:
        file.size,
    };
  }

  let hasRetriedAfterRefresh =
    false;

  while (true) {
    const token =
      await getValidAccessToken();

    const body =
      new FormData();

    body.append(
      "file",
      file
    );

    const headers =
      new Headers();

    if (token) {
      headers.set(
        "Authorization",
        `Bearer ${token}`
      );
    }

    let res: Response;

    try {
      res = await fetch(
        `${BASE_URL}/files/upload`,
        {
          method: "POST",
          headers,
          body,
          cache: "no-store",
        }
      );
    } catch (error) {
      throw error;
    }

    // Successful upload
    if (res.ok) {
      return res.json() as Promise<UploadedFileRef>;
    }

    // Refresh and retry once
    if (
      res.status === 401 &&
      !hasRetriedAfterRefresh
    ) {
      hasRetriedAfterRefresh =
        true;

      const freshToken =
        await refreshAccessToken();

      if (freshToken) {
        continue;
      }

      throw new Error(
        "Your session could not be refreshed."
      );
    }

    const text =
      await res.text().catch(
        () => ""
      );

    throw new Error(
      `API ${res.status}: ${
        text || res.statusText
      }`
    );
  }
}

/**
 * Send a chat message, optionally referencing an uploaded file.
 */
export async function sendChatMessage(
  message: string,
  attachment?:
    | UploadedFileRef
    | null
): Promise<ChatReply> {
  if (AI_MOCK) {
    await wait(1400);

    if (
      attachment ||
      /lineup|export|generate|csv/i.test(
        message
      )
    ) {
      return {
        text:
          "Analysis complete. I've prepared a file with the results.",

        file: {
          name:
            "generated_lineups.csv",

          kind:
            "CSV",

          mime:
            "text/csv",

          content:
            "column_a,column_b\nplaceholder,placeholder\n",
        },
      };
    }

    return {
      text:
        "This is a placeholder response. Once the AI chat API is connected, answers based on your data will appear here.",
    };
  }

  const raw =
    await fetcher<ApiChatResponse>(
      "/chat",
      {
        method: "POST",

        body:
          JSON.stringify({
            message,
            file_id:
              attachment?.id ??
              null,
          }),
      }
    );

  return {
    text:
      raw.reply,

    file:
      raw.file ??
      undefined,
  };
}

/**
 * Trigger a browser download for a generated file.
 */
export function downloadGeneratedFile(
  file: GeneratedFile
) {
  const href =
    file.url
      ? file.url
      : file.id &&
          !AI_MOCK
        ? `${BASE_URL}/files/${file.id}/download`
        : URL.createObjectURL(
            new Blob(
              [
                file.content ??
                  "",
              ],
              {
                type:
                  file.mime,
              }
            )
          );

  const a =
    document.createElement(
      "a"
    );

  a.href =
    href;

  a.download =
    file.name;

  a.rel =
    "noopener";

  document.body.appendChild(
    a
  );

  a.click();

  a.remove();

  if (
    href.startsWith("blob:")
  ) {
    URL.revokeObjectURL(
      href
    );
  }
}

/* ------------------------------------------------------------------ */
/* Dashboard "At a glance"                                             */
/* ------------------------------------------------------------------ */

export interface GlanceStats {
  games: number | null;
  props: number | null;
  lineMovement: number | null;
  injuries: number | null;
}

/**
 * Pulls counts from existing endpoints.
 *
 * Any value that can't be loaded stays null so the dashboard
 * never completely breaks.
 */
export async function getGlanceStats(): Promise<GlanceStats> {
  const [
    gamesRes,
    propsRes,
  ] =
    await Promise.allSettled([
      getGames(),
      getPropsBoard(),
    ]);

  const games =
    gamesRes.status ===
    "fulfilled"
      ? gamesRes.value
      : null;

  const props =
    propsRes.status ===
    "fulfilled"
      ? propsRes.value
      : null;

  return {
    games: games
      ? games.games.length
      : null,

    props: props
      ? props.props.length
      : null,

    lineMovement: games
      ? games.games.filter(
          (g) =>
            g.spreadMove ||
            g.totalMove
        ).length
      : null,

    injuries: null,
  };
}

/**
 * Simple typed fetcher you can pass directly to SWR.
 */
export const swrFetcher =
  <T>(url: string) =>
    fetcher<T>(url);