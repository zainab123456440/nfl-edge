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
      <body className="w-full min-h-screen overflow-x-hidden">
        <AuthProvider>
          {authRoute ? (
            <main className="min-h-screen w-full">
              {children}
            </main>
          ) : (
            <div className="flex min-h-screen w-full flex-col">
              <TopBar />

              <div className="flex min-h-[calc(100vh-64px)] w-full">
                <Sidebar
                  collapsed={collapsed}
                  onToggle={() =>
                    setCollapsed((value) => !value)
                  }
                />

                <main
                  className={`min-w-0 flex-1 w-full transition-all duration-200 ${
                    collapsed ? "pl-16" : "pl-60"
                  }`}
                >
                  <div className="w-full min-w-0">
                    {children}
                  </div>
                </main>
              </div>
            </div>
          )}
        </AuthProvider>
      </body>
    </html>
  );
}