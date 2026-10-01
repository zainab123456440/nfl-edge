"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { cn } from "../../lib/utils";
import { useAuth } from "../../Hooks/useAuth";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "▣" },
  { href: "/games", label: "Games", icon: "⚽" },
  { href: "/props", label: "Player Props", icon: "▤" },
];

type SidebarProps = {
  collapsed: boolean;
  onToggle: () => void;
};

export default function Sidebar({
  collapsed,
  onToggle,
}: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { logout } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    if (loggingOut) return;

    setLoggingOut(true);

    try {
      // useAuth().logout clears the tokens AND sets user to null in
      // AuthProvider, so the login page will not redirect back to
      // the dashboard.
      await logout();
    } catch {
      // Logout is best-effort; local state is cleared regardless.
    } finally {
      router.replace("/login");
    }
  }

  return (
    <aside
      className={cn(
        "fixed bottom-0 left-0 top-16 z-40 border-r border-[var(--border)] bg-[var(--bg)] transition-all duration-200",
        collapsed ? "w-16" : "w-60"
      )}
    >
      <div className="flex h-full flex-col p-2 md:p-4">

        {/* Header */}
        <div
          className={cn(
            "mb-4 flex items-center",
            collapsed ? "justify-center" : "justify-between"
          )}
        >
          {!collapsed && (
            <p className="px-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
              Navigation
            </p>
          )}

          <button
            type="button"
            onClick={onToggle}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--card)] text-[var(--muted)] transition hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
          >
            {collapsed ? "→" : "←"}
          </button>
        </div>

        {/* Navigation */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/dashboard" &&
                pathname.startsWith(`${item.href}/`));

            return (
              <Link
                key={item.href}
                href={item.href}
                title={collapsed ? item.label : undefined}
                className={cn(
                  "flex items-center rounded-lg py-3 text-sm font-medium transition-colors",
                  collapsed
                    ? "justify-center px-2"
                    : "gap-3 px-3",
                  isActive
                    ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--accent)]/50 hover:text-[var(--foreground)]"
                )}
              >
                <span className="flex w-5 shrink-0 items-center justify-center text-base">
                  {item.icon}
                </span>

                {!collapsed && (
                  <span>{item.label}</span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Logout */}
        <div className="mt-auto pt-4">
          <button
            type="button"
            onClick={handleLogout}
            disabled={loggingOut}
            title={collapsed ? "Logout" : undefined}
            className={cn(
              "flex w-full items-center rounded-lg py-3 text-sm font-medium transition-colors",
              "text-[var(--muted-foreground)] hover:bg-red-500/10 hover:text-red-500",
              "disabled:cursor-not-allowed disabled:opacity-50",
              collapsed
                ? "justify-center px-2"
                : "gap-3 px-3"
            )}
          >
            <span className="flex w-5 shrink-0 items-center justify-center text-base">
              {loggingOut ? "…" : "↪"}
            </span>

            {!collapsed && (
              <span>
                {loggingOut ? "Logging out..." : "Logout"}
              </span>
            )}
          </button>
        </div>

      </div>
    </aside>
  );
}