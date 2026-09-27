/**
 * Hooks/useAuth.ts
 *
 * React context + hook for authentication state.
 *
 * Wrap your app (or layout) in ``<AuthProvider>`` and then call
 * ``useAuth()`` anywhere in the tree to get the current user,
 * loading state, and login/signup/logout actions.
 *
 * Token persistence is handled by the AuthAPI service layer — this
 * hook never touches localStorage directly.
 */

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { AuthUser, LoginCredentials, SignupCredentials } from "@/types/auth";
import * as authApi from "@/services/AuthAPI";

// ---------------------------------------------------------------------------
// Context shape
// ---------------------------------------------------------------------------

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (creds: LoginCredentials) => Promise<void>;
  signup: (creds: SignupCredentials) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount: try to restore session from stored tokens.
  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      const token = authApi.getStoredAccessToken();
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const me = await authApi.getMe();
        if (!cancelled) setUser(me);
      } catch {
        // Token might be expired — try refresh.
        const refreshToken = authApi.getStoredRefreshToken();
        if (refreshToken) {
          try {
            const refreshed = await authApi.refreshSession(refreshToken);
            authApi.storeTokens(refreshed.access_token, refreshed.refresh_token);
            const me = await authApi.getMe();
            if (!cancelled) setUser(me);
          } catch {
            authApi.clearTokens();
          }
        } else {
          authApi.clearTokens();
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (creds: LoginCredentials) => {
    const response = await authApi.login(creds);
    authApi.storeTokens(response.access_token, response.refresh_token);
    // Fetch full user info after login.
    const me = await authApi.getMe();
    setUser(me);
  }, []);

  const signup = useCallback(async (creds: SignupCredentials) => {
    const response = await authApi.signup(creds);
    authApi.storeTokens(response.access_token, response.refresh_token);
    const me = await authApi.getMe();
    setUser(me);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Best-effort — clear local state regardless.
    }
    authApi.clearTokens();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      login,
      signup,
      logout,
    }),
    [user, isLoading, login, signup, logout]
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === undefined) {
    throw new Error("useAuth must be used inside an <AuthProvider>.");
  }
  return ctx;
}
