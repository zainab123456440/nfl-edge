// lib/time.ts

/** All times in the app are shown in this US timezone (handles EST/EDT automatically). */
export const APP_TZ = "America/New_York";

/**
 * Week 1 opener (Thursday). The NFL week runs Tuesday to Monday,
 * so week 1 starts on the Tuesday before the opener, at midnight ET.
 * Update this date each season.
 */
const SEASON_OPENER = "2026-09-10T00:00:00-04:00";
const MS_PER_DAY = 86_400_000;

/** "Thu 8:15 PM EDT" */
export function formatKickoff(iso: string, tz: string = APP_TZ): string {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(iso));
}

/** "Thu, Sep 10 · 8:15 PM EDT" (useful for game detail pages) */
export function formatKickoffFull(iso: string, tz: string = APP_TZ): string {
  const d = new Date(iso);
  const date = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    weekday: "short",
    month: "short",
    day: "numeric",
  }).format(d);
  const time = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(d);
  return `${date} · ${time}`;
}

/** Current NFL week (1 to 18). Rolls over Tuesday 12:00 AM ET. */
export function getCurrentWeek(now: Date = new Date()): number {
  const opener = new Date(SEASON_OPENER).getTime();
  const firstTuesday = opener - 2 * MS_PER_DAY; // Tuesday before the opener
  const week = Math.floor((now.getTime() - firstTuesday) / (7 * MS_PER_DAY)) + 1;
  return Math.min(Math.max(week, 1), 18);
}

/** "1d 14h", "3h 20m", "12m" */
export function formatCountdown(ms: number): string {
  if (ms <= 0) return "starting soon";
  const d = Math.floor(ms / MS_PER_DAY);
  const h = Math.floor((ms % MS_PER_DAY) / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}