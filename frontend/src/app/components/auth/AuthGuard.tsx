/**
 * components/auth/AuthGuard.tsx
 *
 * Client-side route protection wrapper.
 *
 * Wraps protected page content and checks the auth context:
 * - While loading: show a full-page loading skeleton.
 * - If not authenticated: redirect to /login.
 * - If authenticated: render children.
 *
 * Usage:
 *   <AuthGuard>
 *     <YourPageContent />
 *   </AuthGuard>
 */

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Leaf } from "lucide-react";
import { useAuth } from "@/Hooks/useAuth";

function AuthLoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-primary">
      <div className="flex flex-col items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-700 animate-gf-pulse">
          <Leaf className="h-5 w-5 text-primary-100" />
        </div>
        <p className="text-sm text-neutral-500">Loading...</p>
      </div>
    </div>
  );
}

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return <AuthLoadingScreen />;
  }

  if (!isAuthenticated) {
    // While the redirect happens, show the loading screen to avoid
    // a flash of protected content.
    return <AuthLoadingScreen />;
  }

  return <>{children}</>;
}
