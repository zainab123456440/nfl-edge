// lib/utils.ts

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes safely (required by shadcn) */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format American odds with + / - sign */
export function formatOdds(price?: number | null): string {
  if (price === undefined || price === null || Number.isNaN(price)) return "—";
  return price > 0 ? `+${price}` : `${price}`;
}

/** Format a number with optional sign (for line moves) */
export function formatMove(value?: number | null, decimals = 1): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}`;
}

/** Format kickoff time nicely (e.g. "Sun 1:00 PM") */
export function formatKickoff(iso: string): string {
  try {
    const date = new Date(iso);
    return new Intl.DateTimeFormat("en-US", {
      weekday: "short",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    }).format(date);
  } catch {
    return "—";
  }
}

/** Short matchup string: "KC @ BUF" */
export function formatMatchup(awayAbbr: string, homeAbbr: string): string {
  return `${awayAbbr} @ ${homeAbbr}`;
}

/** Decide green / red color class based on direction */
export function moveColor(value?: number | null): string {
  if (value === undefined || value === null || value === 0) return "text-muted";
  return value > 0 ? "text-green" : "text-red";
}

/** Simple relative time (optional helper) */
export function timeAgo(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}