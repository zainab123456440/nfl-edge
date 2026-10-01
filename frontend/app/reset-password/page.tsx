/**
 * app/reset-password/page.tsx
 *
 * NFL-EDGE "reset password" page.
 *
 * This is the page the reset-link email points to. The recovery token
 * arrives in the URL hash fragment, e.g.:
 *
 *   /reset-password#access_token=xxx&refresh_token=yyy&type=recovery
 *
 * It is read client-side (hash fragments never reach the server) and
 * sent to the backend together with the new password.
 */

"use client";

import { useEffect, useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, CheckCircle2, AlertTriangle } from "lucide-react";

import Input from "../../components/ui/input";
import Button from "../../components/ui/button";
import AuthLayout from "../../components/auth/AuthLayout";
import { confirmPasswordReset, AuthApiError } from "../../services/AuthAPI";

function readAccessTokenFromHash(): string | null {
  if (typeof window === "undefined") return null;
  const hash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  return new URLSearchParams(hash).get("access_token");
}

type PasswordFieldProps = {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  show: boolean;
  onToggle: () => void;
  hasError?: boolean;
};

function PasswordField({
  id,
  label,
  placeholder,
  value,
  onChange,
  show,
  onToggle,
  hasError,
}: PasswordFieldProps) {
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1 block text-sm font-medium text-slate-300"
      >
        {label}
      </label>
      <div className="relative">
        <Input
          id={id}
          name={id}
          type={show ? "text" : "password"}
          autoComplete="new-password"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required
          className={`pr-10 ${hasError ? "!border-red-500/60" : ""}`}
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-slate-300"
          tabIndex={-1}
          aria-label={show ? "Hide password" : "Show password"}
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  const router = useRouter();

  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [tokenChecked, setTokenChecked] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [shakeError, setShakeError] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setAccessToken(readAccessTokenFromHash());
    setTokenChecked(true);
  }, []);

  const mismatch = confirmPassword.length > 0 && password !== confirmPassword;

  function showError(message: string) {
    setError(message);
    setShakeError(true);
    setTimeout(() => setShakeError(false), 500);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!accessToken) {
      showError("This password reset link is invalid or has expired.");
      return;
    }
    if (password.length < 8) {
      showError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      showError("Passwords do not match.");
      return;
    }

    setIsLoading(true);

    try {
      await confirmPasswordReset(accessToken, password);
      setSuccess(true);
      setTimeout(() => router.push("/login"), 2000);
    } catch (err) {
      showError(
        err instanceof AuthApiError
          ? err.message
          : "Something went wrong. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  }

  // Invalid or missing token
  if (tokenChecked && !accessToken) {
    return (
      <AuthLayout
        title="Invalid reset link"
        subtitle="This password reset link is invalid or has expired."
      >
        <div className="flex flex-col items-center text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-red-500/20 bg-red-500/10">
            <AlertTriangle className="h-6 w-6 text-red-400" />
          </div>
          <p className="mb-6 text-sm text-slate-400">
            Request a new link and we&apos;ll email you a fresh one.
          </p>
          <Link href="/forgot-password" className="w-full">
            <Button type="button" variant="primary" size="lg">
              Request a new link
            </Button>
          </Link>
        </div>
      </AuthLayout>
    );
  }

  // Success
  if (success) {
    return (
      <AuthLayout
        title="Password updated"
        subtitle="Your password has been changed."
      >
        <div className="flex flex-col items-center text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-emerald-500/20 bg-emerald-500/10">
            <CheckCircle2 className="h-6 w-6 text-emerald-400" />
          </div>
          <p className="text-sm text-slate-400">
            Redirecting you to sign in...
          </p>
        </div>
      </AuthLayout>
    );
  }

  // Form
  return (
    <AuthLayout
      title="Set a new password"
      subtitle="Choose a new password for your NFL-EDGE account."
      footer={
        <>
          Back to{" "}
          <Link
            href="/login"
            className="font-semibold text-blue-400 transition hover:text-blue-300"
          >
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate>
        {error && (
          <div
            role="alert"
            className={`mb-5 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300 ${
              shakeError ? "af-shake" : ""
            }`}
          >
            {error}
          </div>
        )}

        <div className="space-y-4">
          <PasswordField
            id="password"
            label="New password"
            placeholder="At least 8 characters"
            value={password}
            onChange={setPassword}
            show={showPassword}
            onToggle={() => setShowPassword((v) => !v)}
          />

          <div>
            <PasswordField
              id="confirmPassword"
              label="Confirm new password"
              placeholder="Re-enter your new password"
              value={confirmPassword}
              onChange={setConfirmPassword}
              show={showConfirm}
              onToggle={() => setShowConfirm((v) => !v)}
              hasError={mismatch}
            />
            {mismatch && (
              <p className="mt-1 text-xs text-red-400">
                Passwords do not match
              </p>
            )}
          </div>
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          isLoading={isLoading}
          loadingText="Updating password..."
          className="mt-6"
        >
          Reset password
        </Button>
      </form>
    </AuthLayout>
  );
}