/**
 * services/AuthAPI.ts
 *
 * The single place the frontend talks to the backend's auth
 * endpoints.  Also manages token persistence in localStorage so
 * the rest of the app never touches storage directly.
 */

import type {
  AuthResponse,
  AuthUser,
  LoginCredentials,
  SignupCredentials,
} from "@/types/auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const REQUEST_TIMEOUT_MS = 15000;

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------

const ACCESS_KEY = "gf_access_token";
const REFRESH_KEY = "gf_refresh_token";

export function getStoredAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function storeTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// ---------------------------------------------------------------------------
// Error class (shared shape with FarmerAPI)
// ---------------------------------------------------------------------------

export class AuthApiError extends Error {
  status: number;
  type: "network" | "timeout" | "validation" | "server" | "auth" | "unknown";

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
// Generic request helper
// ---------------------------------------------------------------------------

async function request<T>(
  path: string,
  init?: RequestInit,
  options?: { includeAuth?: boolean }
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (options?.includeAuth) {
    const token = getStoredAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers,
      signal: controller.signal,
      ...init,
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = await response.json();
        detail = body.detail || detail;
      } catch {
        // ignore JSON parse error
      }

      const type: AuthApiError["type"] =
        response.status === 400 || response.status === 401
          ? "auth"
          : response.status >= 500
            ? "server"
            : "unknown";

      throw new AuthApiError(detail, response.status, type);
    }

    return response.json() as Promise<T>;
  } catch (err) {
    if (err instanceof AuthApiError) throw err;

    if (err instanceof DOMException && err.name === "AbortError") {
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

// ---------------------------------------------------------------------------
// Auth endpoints
// ---------------------------------------------------------------------------

export function signup(creds: SignupCredentials): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify(creds),
  });
}

export function login(creds: LoginCredentials): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(creds),
  });
}

export function refreshSession(refreshToken: string): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function logout(): Promise<void> {
  return request<void>(
    "/api/auth/logout",
    { method: "POST" },
    { includeAuth: true }
  );
}

export function getMe(): Promise<AuthUser> {
  return request<AuthUser>(
    "/api/auth/me",
    undefined,
    { includeAuth: true }
  );
}

// ---------------------------------------------------------------------------
// Password reset
// ---------------------------------------------------------------------------

export function requestPasswordReset(
  contact: string
): Promise<{ detail: string }> {
  return request<{ detail: string }>("/api/auth/reset-password/request", {
    method: "POST",
    body: JSON.stringify({ contact }),
  });
}

export function confirmPasswordReset(
  accessToken: string,
  newPassword: string
): Promise<{ detail: string }> {
  return request<{ detail: string }>("/api/auth/reset-password/confirm", {
    method: "POST",
    body: JSON.stringify({
      access_token: accessToken,
      new_password: newPassword,
    }),
  });
}