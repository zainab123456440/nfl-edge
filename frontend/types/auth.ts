/**
 * types/auth.ts
 *
 * TypeScript shapes for authentication, kept in sync with the backend's
 * authentication schemas.
 */

// ---------------------------------------------------------------------------
// Authenticated user
// ---------------------------------------------------------------------------

export interface AuthUser {
  /**
   * Supabase authenticated user ID.
   *
   * This is the identity used by the backend to isolate
   * user-specific data.
   */
  user_id: string;

  name: string | null;
  email: string | null;
  phone: string | null;
}

// ---------------------------------------------------------------------------
// Authentication tokens
// ---------------------------------------------------------------------------

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

// ---------------------------------------------------------------------------
// Login / signup response
// ---------------------------------------------------------------------------

export interface AuthResponse extends AuthTokens {
  /**
   * Supabase authenticated user ID.
   */
  user_id: string;

  name: string | null;

  /**
   * Indicates whether the backend created a new account
   * during the authentication request.
   */
  is_new: boolean;
}

// ---------------------------------------------------------------------------
// Login credentials
// ---------------------------------------------------------------------------

export interface LoginCredentials {
  contact: string;
  password: string;
}

// ---------------------------------------------------------------------------
// Signup credentials
// ---------------------------------------------------------------------------

export interface SignupCredentials {
  name: string;
  contact: string;
  password: string;
}