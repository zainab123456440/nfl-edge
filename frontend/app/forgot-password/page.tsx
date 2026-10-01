/**
 * app/forgot-password/page.tsx
 *
 * NFL-EDGE "forgot password" page.
 *
 * Collects the user's email and asks the backend to send a reset
 * link (which points to /reset-password). Always shows the same
 * success message, whether or not the email is registered, to avoid
 * leaking account existence.
 */

"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { MailCheck } from "lucide-react";

import Input from "../../components/ui/input";
import Button from "../../components/ui/button";
import AuthLayout from "../../components/auth/AuthLayout";
import { requestPasswordReset, AuthApiError } from "../../services/AuthAPI";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [shakeError, setShakeError] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !email.includes("@")) {
      setError("Please enter a valid email address.");
      setShakeError(true);
      setTimeout(() => setShakeError(false), 500);
      return;
    }

    setIsLoading(true);

    try {
      await requestPasswordReset(email.trim());
      setSubmitted(true);
    } catch (err) {
      setError(
        err instanceof AuthApiError
          ? err.message
          : "Something went wrong. Please try again."
      );
      setShakeError(true);
      setTimeout(() => setShakeError(false), 500);
    } finally {
      setIsLoading(false);
    }
  }

  // Success: same message whether or not the email is registered
  if (submitted) {
    return (
      <AuthLayout
        title="Check your email"
        subtitle="Your reset link is on its way."
      >
        <div className="flex flex-col items-center text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-blue-400/20 bg-blue-500/10">
            <MailCheck className="h-6 w-6 text-blue-400" />
          </div>
          <p className="mb-6 text-sm text-slate-400">
            If an account exists for this email, we&apos;ve sent a link to
            reset your password. It may take a minute to arrive, so check your
            spam folder too.
          </p>
          <Link href="/login" className="w-full">
            <Button type="button" variant="secondary" size="lg">
              Back to sign in
            </Button>
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Forgot your password?"
      subtitle="Enter the email you signed up with and we'll send you a link to reset it."
      footer={
        <>
          Remembered it after all?{" "}
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

        <Input
          label="Email"
          name="email"
          type="email"
          autoComplete="username"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <Button
          type="submit"
          variant="primary"
          size="lg"
          isLoading={isLoading}
          loadingText="Sending link..."
          className="mt-6"
        >
          Send reset link
        </Button>
      </form>
    </AuthLayout>
  );
}