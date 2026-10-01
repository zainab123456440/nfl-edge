"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function getPageName(pathname: string) {
  if (pathname === "/games" || pathname.startsWith("/games/")) {
    return "Games";
  }

  if (pathname === "/props" || pathname.startsWith("/props/")) {
    return "Player Props";
  }

  if (pathname === "/dashboard" || pathname.startsWith("/dashboard/")) {
    return "Dashboard";
  }

  if (pathname === "/") {
    return "Home";
  }

  return "NFL EDGE";
}

export default function TopBar() {
  const pathname = usePathname();
  const pageName = getPageName(pathname);

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--bg)]">
      <div className="flex min-h-16 w-full items-center justify-between px-4 md:px-6">

        {/* Left: Premium Brand */}
        <Link
          href="/"
          className="flex shrink-0 items-center transition-opacity hover:opacity-80"
        >
          <span className="text-[17px] font-bold tracking-[0.22em] text-[var(--foreground)]">
            NFL EDGE
          </span>
        </Link>

        {/* Right: Current Page */}
        <div className="flex items-center">
          <span className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm font-semibold text-[var(--foreground)]">
            {pageName}
          </span>
        </div>

      </div>
    </header>
  );
}