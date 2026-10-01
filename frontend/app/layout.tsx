"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import "./globals.css";
import { AuthProvider } from "../Hooks/useAuth";
import TopBar from "../components/layout/TopBar";
import Sidebar from "../components/layout/Sidebar";

const AUTH_ROUTES = [
  "/login",
  "/signup",
  "/forgot-password",
  "/reset-password",
];

function isAuthRoute(pathname: string): boolean {
  return AUTH_ROUTES.some(
    (route) =>
      pathname === route ||
      pathname.startsWith(`${route}/`)
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const authRoute = isAuthRoute(pathname);

  return (
    <html lang="en">
      <body>
        <AuthProvider>
          {authRoute ? (
            // Authentication pages intentionally have no
            // application navigation.
            <main className="min-h-screen">
              {children}
            </main>
          ) : (
            // Main application pages.
            <>
              <TopBar />

              <div className="flex">
                <Sidebar
                  collapsed={collapsed}
                  onToggle={() =>
                    setCollapsed((value) => !value)
                  }
                />

                <main
                  className={`min-w-0 flex-1 transition-all duration-200 ${
                    collapsed ? "pl-16" : "pl-60"
                  }`}
                >
                  {children}
                </main>
              </div>
            </>
          )}
        </AuthProvider>
      </body>
    </html>
  );
}