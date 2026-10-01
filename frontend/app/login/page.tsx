"use client";

import { useEffect, useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";

import Input from "../../components/ui/input";
import Button from "../../components/ui/button";
import AuthLayout from "../../components/auth/AuthLayout";
import { useAuth } from "../../Hooks/useAuth";
import { AuthApiError } from "../../services/AuthAPI";

export default function LoginPage() {
  const router = useRouter();

  const {
    login,
    isAuthenticated,
    isLoading: authLoading,
  } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // -------------------------------------------------------------------------
  // Already authenticated users should not stay on the login page.
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [authLoading, isAuthenticated, router]);

  // -------------------------------------------------------------------------
  // Login
  // -------------------------------------------------------------------------

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    setError(null);
    setIsLoading(true);

    try {
      await login({
        contact: email.trim(),
        password,
      });

      // Successful authentication always enters the application
      // through the dashboard.
      router.replace("/dashboard");
    } catch (err) {
      const message =
        err instanceof AuthApiError
          ? err.message
          : "Unable to sign in. Please check your email and password.";

      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  // Don't render the login form while restoring an existing session.
  if (authLoading || isAuthenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div
          className="h-6 w-6 animate-spin rounded-full border-2 border-slate-500 border-t-white"
          aria-label="Loading"
        />
      </main>
    );
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to continue to NFL-EDGE"
      footer={
        <>
          Don&apos;t have an account?{" "}
          <Link
            href="/signup"
            className="font-semibold text-blue-400 transition hover:text-blue-300"
          >
            Create account
          </Link>
        </>
      }
    >
      {error && (
        <div
          role="alert"
          className="mb-5 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300"
        >
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <div className="space-y-4">
          <Input
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <div>
            <div className="mb-1 flex items-center justify-between">
              <label
                htmlFor="password"
                className="text-sm font-medium text-slate-300"
              >
                Password
              </label>

              <Link
                href="/forgot-password"
                className="text-sm font-medium text-blue-400 transition hover:text-blue-300"
              >
                Forgot password?
              </Link>
            </div>

            <div className="relative">
              <Input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="pr-10"
              />

              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-slate-300"
                aria-label={
                  showPassword ? "Hide password" : "Show password"
                }
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          isLoading={isLoading}
          loadingText="Signing in..."
          className="mt-6"
        >
          Sign in
        </Button>
      </form>
    </AuthLayout>
  );
}