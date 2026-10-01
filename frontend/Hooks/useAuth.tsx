/**
 * Hooks/useAuth.tsx
 *
 * Central authentication context for the application.
 *
 * Provides:
 * - Current authenticated user
 * - Loading state while restoring a session
 * - Login / signup / logout actions
 * - A single source of truth for protected frontend routes
 *
 * Token persistence is handled by the AuthAPI service layer.
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
import type {
  AuthUser,
  LoginCredentials,
  SignupCredentials,
} from "../types/auth";
import * as authApi from "../services/AuthAPI";

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

export function AuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // -------------------------------------------------------------------------
  // Restore existing authentication session
  // -------------------------------------------------------------------------

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      try {
        const accessToken = authApi.getStoredAccessToken();

        // No stored access token means the user is logged out.
        if (!accessToken) {
          return;
        }

        try {
          // First try the existing access token.
          const me = await authApi.getMe();

          if (!cancelled) {
            setUser(me);
          }

          return;
        } catch {
          // Access token may have expired.
        }

        // Try refreshing the session.
        const refreshToken = authApi.getStoredRefreshToken();

        if (!refreshToken) {
          authApi.clearTokens();
          return;
        }

        try {
          const refreshed = await authApi.refreshSession(refreshToken);

          if (cancelled) {
            return;
          }

          authApi.storeTokens(
            refreshed.access_token,
            refreshed.refresh_token
          );

          const me = await authApi.getMe();

          if (!cancelled) {
            setUser(me);
          }
        } catch {
          // Refresh failed — treat the session as expired.
          authApi.clearTokens();

          if (!cancelled) {
            setUser(null);
          }
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    restoreSession();

    return () => {
      cancelled = true;
    };
  }, []);

  // -------------------------------------------------------------------------
  // Login
  // -------------------------------------------------------------------------

  const login = useCallback(async (creds: LoginCredentials) => {
    const response = await authApi.login(creds);

    authApi.storeTokens(
      response.access_token,
      response.refresh_token
    );

    const me = await authApi.getMe();

    setUser(me);
  }, []);

  // -------------------------------------------------------------------------
  // Signup
  // -------------------------------------------------------------------------

  const signup = useCallback(async (creds: SignupCredentials) => {
    const response = await authApi.signup(creds);

    authApi.storeTokens(
      response.access_token,
      response.refresh_token
    );

    const me = await authApi.getMe();

    setUser(me);
  }, []);

  // -------------------------------------------------------------------------
  // Logout
  // -------------------------------------------------------------------------

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Logout is best-effort.
      // Local authentication state must still be cleared.
    } finally {
      authApi.clearTokens();
      setUser(null);
    }
  }, []);

  // -------------------------------------------------------------------------
  // Context value
  // -------------------------------------------------------------------------

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

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error("useAuth must be used inside an <AuthProvider>.");
  }

  return context;
}