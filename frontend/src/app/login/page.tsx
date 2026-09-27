/**
 * app/login/page.tsx
 *
 * Green Flora login page.
 *
 * Renders inside AuthLayout (nature-inspired background, centered card).
 * Provides email + password login with show/hide toggle, a forgot-password
 * link, a simple English/Urdu text toggle, loading state, inline error
 * display, and a link to the signup page.
 *
 * NOTE: Phone-based login has been removed. The backend only accepts
 * an email address for the "contact" field (see services/auth_service.py).
 *
 * NOTE: The language toggle here is intentionally simple and local to
 * this page (just a few strings swapped via useState) — it does not
 * share state with the dashboard's language system. If you later want
 * this page to follow the same language as the dashboard, it needs to
 * be wired into that shared context/provider instead.
 */

"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";

import AuthLayout from "@/components/layout/AuthLayout";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useAuth } from "@/Hooks/useAuth";
import { AuthApiError } from "@/services/AuthAPI";

type Lang = "en" | "ur";

const TEXT: Record<Lang, {
  title: string;
  subtitle: string;
  emailLabel: string;
  passwordLabel: string;
  forgot: string;
  submit: string;
  noAccount: string;
  createAccount: string;
  toggleLabel: string;
}> = {
  en: {
    title: "Welcome back",
    subtitle: "Sign in to your Green Flora account",
    emailLabel: "Email",
    passwordLabel: "Password",
    forgot: "Forgot password?",
    submit: "Sign In",
    noAccount: "Don't have an account?",
    createAccount: "Create account",
    toggleLabel: "اردو",
  },
  ur: {
    title: "خوش آمدید",
    subtitle: "اپنے گرین فلورا اکاؤنٹ میں سائن ان کریں",
    emailLabel: "ای میل",
    passwordLabel: "پاس ورڈ",
    forgot: "پاس ورڈ بھول گئے؟",
    submit: "سائن ان",
    noAccount: "اکاؤنٹ نہیں ہے؟",
    createAccount: "اکاؤنٹ بنائیں",
    toggleLabel: "English",
  },
};

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [lang, setLang] = useState<Lang>("en");
  const t = TEXT[lang];

  const [contact, setContact] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [shakeError, setShakeError] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login({ contact: contact.trim(), password });
      router.push("/dashboard");
    } catch (err) {
      const message =
        err instanceof AuthApiError
          ? err.message
          : "Something went wrong. Please try again.";
      setError(message);
      setShakeError(true);
      setTimeout(() => setShakeError(false), 500);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <AuthLayout>
      <div className="mb-2 flex justify-end">
        <button
          type="button"
          onClick={() => setLang((v) => (v === "en" ? "ur" : "en"))}
          className="text-sm font-medium text-primary-700 hover:text-primary-800 transition-colors"
        >
          {t.toggleLabel}
        </button>
      </div>

      <form onSubmit={handleSubmit} noValidate dir={lang === "ur" ? "rtl" : "ltr"}>
        <h1 className="mb-1 text-lg font-semibold text-neutral-900">
          {t.title}
        </h1>
        <p className="mb-6 text-sm text-neutral-500">{t.subtitle}</p>

        {error && (
          <div
            className={`mb-4 rounded-md bg-danger-50 border border-danger-100 px-3 py-2.5 text-sm text-danger-600 ${
              shakeError ? "animate-gf-shake" : ""
            }`}
            role="alert"
          >
            {error}
          </div>
        )}

        <div className="space-y-4">
          <Input
            label={t.emailLabel}
            name="contact"
            type="email"
            autoComplete="username"
            placeholder="you@example.com"
            value={contact}
            onChange={(e) => setContact(e.target.value)}
            required
          />

          <div className="relative">
            <div className="mb-1 flex items-center justify-between">
              <label
                htmlFor="password"
                className="text-sm font-medium text-neutral-700"
              >
                {t.passwordLabel}
              </label>
              <Link
                href="/forgot-password"
                className="text-sm font-medium text-primary-700 hover:text-primary-800 transition-colors"
                tabIndex={0}
              >
                {t.forgot}
              </Link>
            </div>
            <Input
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

        <p className="mt-5 text-center text-sm text-neutral-500">
          {t.noAccount}{" "}
          <Link
            href="/signup"
            className="font-medium text-primary-700 hover:text-primary-800 transition-colors"
          >
            {t.createAccount}
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}