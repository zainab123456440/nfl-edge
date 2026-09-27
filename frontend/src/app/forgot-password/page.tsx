/**
 * app/forgot-password/page.tsx
 *
 * Green Flora "forgot password" page.
 *
 * Collects the user's email and asks the backend to send a reset
 * link (which points to /reset-password). Always shows the same
 * success message, whether or not the email is registered, to avoid
 * leaking account existence.
 *
 * NOTE: Same simple, page-local EN/UR toggle as login/page.tsx —
 * not wired into any shared dashboard language context.
 */

"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";

import AuthLayout from "@/components/layout/AuthLayout";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { requestPasswordReset, AuthApiError } from "@/services/AuthAPI";

type Lang = "en" | "ur";

const TEXT: Record<Lang, {
  title: string;
  subtitle: string;
  emailLabel: string;
  submit: string;
  back: string;
  rememberedIt: string;
  checkTitle: string;
  checkBody: string;
  toggleLabel: string;
}> = {
  en: {
    title: "Forgot your password?",
    subtitle:
      "Enter the email you signed up with and we'll send you a link to reset it.",
    emailLabel: "Email",
    submit: "Send reset link",
    back: "Back to sign in",
    rememberedIt: "Remembered it after all?",
    checkTitle: "Check your email",
    checkBody:
      "If an account exists for this email, we've sent a link to reset your password. It may take a minute to arrive — check your spam folder too.",
    toggleLabel: "اردو",
  },
  ur: {
    title: "پاس ورڈ بھول گئے؟",
    subtitle:
      "وہ ای میل درج کریں جس سے آپ نے سائن اپ کیا تھا، ہم آپ کو ری سیٹ لنک بھیجیں گے۔",
    emailLabel: "ای میل",
    submit: "ری سیٹ لنک بھیجیں",
    back: "سائن ان پر واپس جائیں",
    rememberedIt: "یاد آ گیا؟",
    checkTitle: "اپنا ای میل چیک کریں",
    checkBody:
      "اگر اس ای میل کے ساتھ کوئی اکاؤنٹ موجود ہے تو ہم نے پاس ورڈ ری سیٹ کرنے کا لنک بھیج دیا ہے۔ اسپیم فولڈر بھی چیک کریں۔",
    toggleLabel: "English",
  },
};

export default function ForgotPasswordPage() {
  const [lang, setLang] = useState<Lang>("en");
  const t = TEXT[lang];

  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await requestPasswordReset(email.trim());
      setSubmitted(true);
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

  if (submitted) {
    return (
      <AuthLayout>
        {LangToggle}
        <div dir={lang === "ur" ? "rtl" : "ltr"}>
          <h1 className="mb-1 text-lg font-semibold text-neutral-900">
            {t.checkTitle}
          </h1>
          <p className="mb-6 text-sm text-neutral-500">
            {t.checkBody}
          </p>
          <Link
            href="/login"
            className="text-sm font-medium text-primary-700 hover:text-primary-800 transition-colors"
          >
            {t.back}
          </Link>
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

        <Input
          label={t.emailLabel}
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
          className="mt-6 w-full"
        >
          {t.submit}
        </Button>

        <p className="mt-5 text-center text-sm text-neutral-500">
          {t.rememberedIt}{" "}
          <Link
            href="/login"
            className="font-medium text-primary-700 hover:text-primary-800 transition-colors"
          >
            {t.back}
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}