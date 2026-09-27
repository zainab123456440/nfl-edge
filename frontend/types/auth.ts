/**
 * types/auth.ts
 *
 * TypeScript shapes for authentication, kept in sync with the backend's
 * schemas/auth.py.
 */

export interface AuthUser {
  user_id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

export interface AuthResponse extends AuthTokens {
  user_id: string;
  name: string | null;
  is_new: boolean;
}

export interface LoginCredentials {
  contact: string;
  password: string;
}

export interface SignupCredentials {
  name: string;
  contact: string;
  password: string;
}
