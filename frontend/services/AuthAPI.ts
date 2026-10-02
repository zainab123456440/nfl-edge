import type {
  AuthResponse,
  AuthUser,
  LoginCredentials,
  SignupCredentials,
} from "../types/auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "https://nfl-backend-eight.vercel.app";

const REQUEST_TIMEOUT_MS = 15000;
const LOGOUT_TIMEOUT_MS = 4000;

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------

const ACCESS_KEY = "gf_access_token";
const REFRESH_KEY = "gf_refresh_token";

export function getStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return localStorage.getItem(ACCESS_KEY);
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return localStorage.getItem(REFRESH_KEY);
}

export function storeTokens(
  access: string,
  refresh: string
): void {
  if (typeof window === "undefined") {
    return;
  }

  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  if (typeof window === "undefined") {
    return;
  }

  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// ---------------------------------------------------------------------------
// Error class
// ---------------------------------------------------------------------------

export class AuthApiError extends Error {
  status: number;

  type:
    | "network"
    | "timeout"
    | "validation"
    | "server"
    | "auth"
    | "unknown";

  constructor(
    message: string,
    status: number,
    type: AuthApiError["type"] = "unknown"
  ) {
    super(message);

    this.name = "AuthApiError";
    this.status = status;
    this.type = type;
  }
}

// ---------------------------------------------------------------------------
// Refresh / logout state
// ---------------------------------------------------------------------------

let refreshPromise: Promise<AuthResponse | null> | null = null;

/*
 * Set to true while (and after) the user logs out. Prevents an in-flight
 * token refresh from writing fresh tokens back to storage after logout.
 * Reset to false by login() and signup().
 */
let isLoggingOut = false;

// ---------------------------------------------------------------------------
// Token refresh
// ---------------------------------------------------------------------------

async function performRefresh(
  refreshToken: string
): Promise<AuthResponse | null> {
  const controller = new AbortController();

  const timeoutId = setTimeout(
    () => controller.abort(),
    REQUEST_TIMEOUT_MS
  );

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/auth/refresh`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
        signal: controller.signal,
      }
    );

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as AuthResponse;
  } catch {
    return null;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function refreshAccessToken(): Promise<string | null> {
  if (typeof window === "undefined" || isLoggingOut) {
    return null;
  }

  const refreshToken = getStoredRefreshToken();

  if (!refreshToken) {
    return null;
  }

  /*
   * If several requests discover an expired token at the same time,
   * they all share one refresh request.
   */
  if (!refreshPromise) {
    refreshPromise = performRefresh(refreshToken).finally(() => {
      refreshPromise = null;
    });
  }

  const result = await refreshPromise;

  /*
   * If the user logged out while the refresh was running,
   * do not save anything.
   */
  if (!result || isLoggingOut) {
    return null;
  }

  if (
    !result.access_token ||
    !result.refresh_token
  ) {
    clearTokens();
    return null;
  }

  storeTokens(
    result.access_token,
    result.refresh_token
  );

  return result.access_token;
}

// ---------------------------------------------------------------------------
// Get a usable access token
// ---------------------------------------------------------------------------

/**
 * Returns the current access token.
 *
 * If the JWT is expired or will expire very soon, refresh it first.
 *
 * This is useful for components such as the AI Assistant that use
 * their own fetch()/SSE requests instead of the generic request() helper.
 */
export async function getValidAccessToken(): Promise<string | null> {
  const token = getStoredAccessToken();

  if (!token) {
    return refreshAccessToken();
  }

  try {
    const parts = token.split(".");

    if (parts.length !== 3) {
      return token;
    }

    const payload = JSON.parse(
      atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"))
    );

    const exp =
      typeof payload?.exp === "number"
        ? payload.exp
        : null;

    if (!exp) {
      return token;
    }

    const now = Math.floor(Date.now() / 1000);

    /*
     * Refresh when the token has expired or has less than 60 seconds
     * remaining. This prevents an AI request from starting with a token
     * that expires while the request is running.
     */
    if (exp - now <= 60) {
      const refreshed = await refreshAccessToken();

      return refreshed || null;
    }

    return token;
  } catch {
    /*
     * If the token cannot be decoded, let the backend validate it.
     */
    return token;
  }
}

// ---------------------------------------------------------------------------
// Generic request helper
// ---------------------------------------------------------------------------

async function request<T>(
  path: string,
  init?: RequestInit,
  options?: {
    includeAuth?: boolean;
  }
): Promise<T> {
  const includeAuth = options?.includeAuth === true;

  let hasRetriedAfterRefresh = false;

  while (true) {
    const controller = new AbortController();

    const timeoutId = setTimeout(
      () => controller.abort(),
      REQUEST_TIMEOUT_MS
    );

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (includeAuth) {
      const token = getStoredAccessToken();

      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}${path}`,
        {
          ...init,
          headers: {
            ...headers,
            ...(init?.headers || {}),
          },
          signal: controller.signal,
        }
      );

      // ---------------------------------------------------------------
      // Successful response
      // ---------------------------------------------------------------

      if (response.ok) {
        if (response.status === 204) {
          return undefined as T;
        }

        const contentType =
          response.headers.get("content-type") || "";

        if (!contentType.includes("application/json")) {
          return undefined as T;
        }

        return (await response.json()) as T;
      }

      // ---------------------------------------------------------------
      // Unauthorized
      // ---------------------------------------------------------------

      if (
        response.status === 401 &&
        includeAuth &&
        !hasRetriedAfterRefresh
      ) {
        hasRetriedAfterRefresh = true;

        const freshAccessToken =
          await refreshAccessToken();

        if (freshAccessToken) {
          continue;
        }

        clearTokens();
      }

      // ---------------------------------------------------------------
      // Backend error
      // ---------------------------------------------------------------

      let detail =
        response.statusText ||
        "Request failed.";

      try {
        const body = await response.json();

        if (typeof body?.detail === "string") {
          detail = body.detail;
        } else if (
          typeof body?.message === "string"
        ) {
          detail = body.message;
        }
      } catch {
        // Response may not contain JSON.
      }

      const type: AuthApiError["type"] =
        response.status === 400 ||
        response.status === 401
          ? "auth"
          : response.status === 422
            ? "validation"
            : response.status >= 500
              ? "server"
              : "unknown";

      throw new AuthApiError(
        detail,
        response.status,
        type
      );
    } catch (err) {
      if (err instanceof AuthApiError) {
        throw err;
      }

      if (
        err instanceof DOMException &&
        err.name === "AbortError"
      ) {
        throw new AuthApiError(
          "Request timed out. Please check your connection.",
          408,
          "timeout"
        );
      }

      throw new AuthApiError(
        "Network error. Please check your connection.",
        0,
        "network"
      );
    } finally {
      clearTimeout(timeoutId);
    }
  }
}

// ---------------------------------------------------------------------------
// Authentication endpoints
// ---------------------------------------------------------------------------

export async function signup(
  creds: SignupCredentials
): Promise<AuthResponse> {
  isLoggingOut = false;

  const result = await request<AuthResponse>(
    "/api/auth/signup",
    {
      method: "POST",
      body: JSON.stringify(creds),
    }
  );

  if (
    result.access_token &&
    result.refresh_token
  ) {
    storeTokens(
      result.access_token,
      result.refresh_token
    );
  }

  return result;
}

export async function login(
  creds: LoginCredentials
): Promise<AuthResponse> {
  isLoggingOut = false;

  const result = await request<AuthResponse>(
    "/api/auth/login",
    {
      method: "POST",
      body: JSON.stringify(creds),
    }
  );

  if (
    result.access_token &&
    result.refresh_token
  ) {
    storeTokens(
      result.access_token,
      result.refresh_token
    );
  }

  return result;
}

export async function refreshSession(
  refreshToken: string
): Promise<AuthResponse> {
  const result = await request<AuthResponse>(
    "/api/auth/refresh",
    {
      method: "POST",
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    }
  );

  if (
    !isLoggingOut &&
    result.access_token &&
    result.refresh_token
  ) {
    storeTokens(
      result.access_token,
      result.refresh_token
    );
  }

  return result;
}

// ---------------------------------------------------------------------------
// Logout
// ---------------------------------------------------------------------------

export async function logout(): Promise<void> {
  /*
   * 1. Block any in-flight or future refresh from re-saving tokens.
   * 2. Grab the current access token, then wipe the local session
   *    immediately, so the user is logged out locally no matter what
   *    the backend does.
   */
  isLoggingOut = true;

  const token = getStoredAccessToken();

  clearTokens();
  refreshPromise = null;

  if (!token) {
    return;
  }

  /*
   * 3. Tell the backend, but never wait long and never fail because of it.
   */
  const controller = new AbortController();

  const timeoutId = setTimeout(
    () => controller.abort(),
    LOGOUT_TIMEOUT_MS
  );

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/auth/logout`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        signal: controller.signal,
      }
    );

    if (!response.ok && response.status !== 401) {
      console.warn(
        "Backend logout returned:",
        response.status
      );
    }
  } catch {
    /*
     * Non-critical: the local session is already cleared.
     */
  } finally {
    clearTimeout(timeoutId);
  }
}

export function getMe(): Promise<AuthUser> {
  return request<AuthUser>(
    "/api/auth/me",
    undefined,
    {
      includeAuth: true,
    }
  );
}

// ---------------------------------------------------------------------------
// Password reset
// ---------------------------------------------------------------------------

export function requestPasswordReset(
  contact: string
): Promise<{ detail: string }> {
  return request<{ detail: string }>(
    "/api/auth/reset-password/request",
    {
      method: "POST",
      body: JSON.stringify({
        contact,
      }),
    }
  );
}

export function confirmPasswordReset(
  accessToken: string,
  newPassword: string
): Promise<{ detail: string }> {
  return request<{ detail: string }>(
    "/api/auth/reset-password/confirm",
    {
      method: "POST",
      body: JSON.stringify({
        access_token: accessToken,
        new_password: newPassword,
      }),
    }
  );
}