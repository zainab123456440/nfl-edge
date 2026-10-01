/**
 * Hooks/useAuth.tsx
 *
 * Central authentication context for the application.
 *
 * Responsibilities:
 * - Restore the user's session on app startup
 * - Refresh expired access tokens
 * - Keep frontend auth state synchronized with localStorage
 * - Provide login / signup / logout actions
 * - Prevent stale authentication state from remaining in the UI
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

const AuthContext =
  createContext<AuthContextValue | undefined>(undefined);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [user, setUser] =
    useState<AuthUser | null>(null);

  const [isLoading, setIsLoading] =
    useState(true);

  // -------------------------------------------------------------------------
  // Restore session
  // -------------------------------------------------------------------------

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      try {
        /*
         * Always start by checking whether we have a local access token.
         */
        const accessToken =
          authApi.getStoredAccessToken();

        if (!accessToken) {
          if (!cancelled) {
            setUser(null);
          }

          return;
        }

        /*
         * getMe() uses the authenticated request helper.
         *
         * If the access token has expired, AuthAPI.request()
         * automatically attempts a refresh before giving up.
         */
        try {
          const me = await authApi.getMe();

          if (!cancelled) {
            setUser(me);
          }

          return;
        } catch {
          /*
           * getMe() failed.
           *
           * At this point AuthAPI has already attempted the refresh.
           * We therefore check whether a usable token still exists.
           */
        }

        /*
         * If getMe() failed, explicitly attempt one final refresh
         * using the stored refresh token.
         *
         * This protects against cases where the access token expired
         * between the initial session check and the API request.
         */
        const refreshToken =
          authApi.getStoredRefreshToken();

        if (!refreshToken) {
          authApi.clearTokens();

          if (!cancelled) {
            setUser(null);
          }

          return;
        }

        try {
          const refreshed =
            await authApi.refreshSession(refreshToken);

          if (cancelled) {
            return;
          }

          /*
           * AuthAPI.refreshSession() already stores the tokens,
           * but storing them here as well keeps this flow explicit
           * and safe if the implementation changes later.
           */
          if (
            refreshed?.access_token &&
            refreshed?.refresh_token
          ) {
            authApi.storeTokens(
              refreshed.access_token,
              refreshed.refresh_token
            );
          }

          /*
           * Fetch the authenticated user again using
           * the new access token.
           */
          const me = await authApi.getMe();

          if (!cancelled) {
            setUser(me);
          }
        } catch {
          /*
           * Both access-token validation and refresh failed.
           *
           * This is a genuinely expired/invalid session.
           */
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

  const login = useCallback(
    async (creds: LoginCredentials) => {
      /*
       * AuthAPI.login() resets the logout lock and stores the
       * returned tokens.
       */
      const response =
        await authApi.login(creds);

      /*
       * Keep this explicit as well.
       */
      if (
        response?.access_token &&
        response?.refresh_token
      ) {
        authApi.storeTokens(
          response.access_token,
          response.refresh_token
        );
      }

      /*
       * Load the authenticated user using the fresh token.
       */
      const me = await authApi.getMe();

      setUser(me);
    },
    []
  );

  // -------------------------------------------------------------------------
  // Signup
  // -------------------------------------------------------------------------

  const signup = useCallback(
    async (creds: SignupCredentials) => {
      const response =
        await authApi.signup(creds);

      if (
        response?.access_token &&
        response?.refresh_token
      ) {
        authApi.storeTokens(
          response.access_token,
          response.refresh_token
        );
      }

      const me = await authApi.getMe();

      setUser(me);
    },
    []
  );

  // -------------------------------------------------------------------------
  // Logout
  // -------------------------------------------------------------------------

  const logout = useCallback(async () => {
    /*
     * AuthAPI.logout() clears local tokens immediately and prevents
     * a background refresh from writing tokens back.
     */
    try {
      await authApi.logout();
    } catch {
      /*
       * Backend logout is best-effort.
       *
       * The local session must still be cleared.
       */
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
    [
      user,
      isLoading,
      login,
      signup,
      logout,
    ]
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
  const context =
    useContext(AuthContext);

  if (context === undefined) {
    throw new Error(
      "useAuth must be used inside an <AuthProvider>."
    );
  }

  return context;
}