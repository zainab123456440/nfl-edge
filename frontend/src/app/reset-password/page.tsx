/**
 * app/reset-password/page.tsx
 *
 * Green Flora "reset password" page.
 *
 * This is the page Supabase's reset-link email points to. Supabase
 * appends the recovery token to the URL as a hash fragment, e.g.:
 *
 *   /reset-password#access_token=xxx&refresh_token=yyy&type=recovery
 *
 * We read it client-side (hash fragments never reach the server) and
 * post it to the backend along with the new password.
 *
 * NOTE: Same simple, page-local EN/UR toggle as the other auth pages —
 * not wired into any shared dashboard language context.
 */

"use client";

import { useEffect, useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";

import AuthLayout from "@/components/layout/AuthLayout";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { confirmPasswordReset, AuthApiError } from "@/services/AuthAPI";

type Lang = "en" | "ur";

const TEXT: Record<Lang, {
  title: string;
  subtitle: string;
  newPassword: string;
  confirmPassword: string;
  submit: string;
  invalidTitle: string;
  invalidBody: string;
  requestNew: string;
  successTitle: string;
  successBody: string;
  toggleLabel: string;
}> = {
  en: {
    title: "Set a new password",
    subtitle: "Choose a new password for your Green Flora account.",
    newPassword: "New password",
    confirmPassword: "Confirm new password",
    submit: "Reset password",
    invalidTitle: "Invalid reset link",
    invalidBody:
      "This password reset link is invalid or has expired. Please request a new one.",
    requestNew: "Request a new link",
    successTitle: "Password reset",
    successBody: "Your password has been updated. Redirecting you to sign in...",
    toggleLabel: "اردو",
  },
  ur: {
    title: "نیا پاس ورڈ سیٹ کریں",
    subtitle: "اپنے گرین فلورا اکاؤنٹ کے لیے نیا پاس ورڈ منتخب کریں۔",
    newPassword: "نیا پاس ورڈ",
    confirmPassword: "نئے پاس ورڈ کی تصدیق کریں",
    submit: "پاس ورڈ ری سیٹ کریں",
    invalidTitle: "غلط ری سیٹ لنک",
    invalidBody:
      "یہ پاس ورڈ ری سیٹ لنک غلط ہے یا میعاد ختم ہو چکی ہے۔ براہ کرم نیا لنک حاصل کریں۔",
    requestNew: "نیا لنک حاصل کریں",
    successTitle: "پاس ورڈ ری سیٹ ہو گیا",
    successBody: "آپ کا پاس ورڈ اپ ڈیٹ کر دیا گیا ہے۔ سائن ان پر بھیجا جا رہا ہے...",
    toggleLabel: "English",
  },
};

function readAccessTokenFromHash(): string | null {
  if (typeof window === "undefined") return null;
  const hash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  const params = new URLSearchParams(hash);
  return params.get("access_token");
}

export default function ResetPasswordPage() {
  const router = useRouter();

  const [lang, setLang] = useState<Lang>("en");
  const t = TEXT[lang];

  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [tokenChecked, setTokenChecked] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setAccessToken(readAccessTokenFromHash());
    setTokenChecked(true);
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!accessToken) {
      setError(t.invalidBody);
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }

    setIsLoading(true);
    try {
      await confirmPasswordReset(accessToken, password);
      setSuccess(true);
      setTimeout(() => router.push("/login"), 2000);
    } catch (err) {
      const message =
        err instanceof AuthApiError
          ? err.message
          : "Something went wrong. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  const LangToggle = (
    <div className="mb-2 flex justify-end">
      <button
        type="button"
        onClick={() => setLang((v) => (v === "en" ? "ur" : "en"))}
        className="text-sm font-medium text-primary-700 hover:text-primary-800 transition-colors"
      >
        {t.toggleLabel}
      </button>
    </div>
  );

  if (tokenChecked && !accessToken) {
    return (
      <AuthLayout>
        {LangToggle}
        <div dir={lang === "ur" ? "rtl" : "ltr"}>
          <h1 className="mb-1 text-lg font-semibold text-neutral-900">
            {t.invalidTitle}
          </h1>
          <p className="mb-6 text-sm text-neutral-500">{t.invalidBody}</p>
          <Link
            href="/forgot-password"
            className="text-sm font-medium text-primary-700 hover:text-primary-800 transition-colors"
          >
            {t.requestNew}
          </Link>
        </div>
      </AuthLayout>
    );
  }

  if (success) {
    return (
      <AuthLayout>
        {LangToggle}
        <div dir={lang === "ur" ? "rtl" : "ltr"}>
          <h1 className="mb-1 text-lg font-semibold text-neutral-900">
            {t.successTitle}
          </h1>
          <p className="text-sm text-neutral-500">{t.successBody}</p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      {LangToggle}
      <form onSubmit={handleSubmit} noValidate dir={lang === "ur" ? "rtl" : "ltr"}>
        <h1 className="mb-1 text-lg font-semibold text-neutral-900">
          {t.title}
        </h1>
        <p className="mb-6 text-sm text-neutral-500">{t.subtitle}</p>

        {error && (
          <div
            className="mb-4 rounded-md bg-danger-50 border border-danger-100 px-3 py-2.5 text-sm text-danger-600"
            role="alert"
          >
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div className="relative">
            <Input
              label={t.newPassword}
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="pr-10"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-[34px] text-neutral-400 hover:text-neutral-600 transition-colors"
              tabIndex={-1}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>

          <Input
            label={t.confirmPassword}
            name="confirmPassword"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            placeholder="Re-enter your new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          isLoading={isLoading}
          className="mt-6 w-full"
        >
          {t.submit}
        </Button>
      </form>
    </AuthLayout>
  );
}