/**
 * app/signup/page.tsx
 *
 * NFL-EDGE signup page.
 * Collects name, email and password, with client-side validation,
 * a password strength meter and a confirm-password check.
 */

"use client";

import { useEffect, useState, useMemo, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";

import Input from "../../components/ui/input";
import Button from "../../components/ui/button";
import AuthLayout from "../../components/auth/AuthLayout";
import { useAuth } from "../../Hooks/useAuth";
import { AuthApiError } from "../../services/AuthAPI";

// ---------------------------------------------------------------------------
// Password strength
// ---------------------------------------------------------------------------

type Strength = "weak" | "fair" | "good" | "strong";

function getPasswordStrength(pw: string): {
  score: number;
  label: Strength;
} {
  if (!pw) {
    return { score: 0, label: "weak" };
  }

  let score = 0;

  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;

  if (score <= 1) {
    return { score: 1, label: "weak" };
  }

  if (score === 2) {
    return { score: 2, label: "fair" };
  }

  if (score === 3) {
    return { score: 3, label: "good" };
  }

  return { score: 4, label: "strong" };
}

const strengthColors: Record<Strength, string> = {
  weak: "bg-red-500",
  fair: "bg-amber-500",
  good: "bg-blue-500",
  strong: "bg-emerald-500",
};

const strengthLabels: Record<Strength, string> = {
  weak: "Weak",
  fair: "Fair",
  good: "Good",
  strong: "Strong",
};

// ---------------------------------------------------------------------------
// Password field
// ---------------------------------------------------------------------------

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
          className={`pr-10 ${
            hasError ? "!border-red-500/60" : ""
          }`}
        />

        <button
          type="button"
          onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-slate-300"
          tabIndex={-1}
          aria-label={show ? "Hide password" : "Show password"}
        >
          {show ? (
            <EyeOff className="h-4 w-4" />
          ) : (
            <Eye className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SignupPage() {
  const router = useRouter();

  const {
    signup,
    isAuthenticated,
    isLoading: authLoading,
  } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [shakeError, setShakeError] = useState(false);

  const strength = useMemo(
    () => getPasswordStrength(password),
    [password]
  );

  const mismatch =
    confirmPassword.length > 0 &&
    password !== confirmPassword;

  // -------------------------------------------------------------------------
  // Already authenticated users should not stay on signup.
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [authLoading, isAuthenticated, router]);

  // -------------------------------------------------------------------------
  // Validation
  // -------------------------------------------------------------------------

  function validate(): string | null {
    if (!name.trim()) {
      return "Please enter your name.";
    }

    if (!email.trim()) {
      return "Please enter your email address.";
    }

    if (!email.includes("@")) {
      return "Please enter a valid email address.";
    }

    if (password.length < 8) {
      return "Password must be at least 8 characters.";
    }

    if (password !== confirmPassword) {
      return "Passwords do not match.";
    }

    return null;
  }

  function showError(message: string) {
    setError(message);
    setShakeError(true);

    setTimeout(() => {
      setShakeError(false);
    }, 500);
  }

  // -------------------------------------------------------------------------
  // Signup
  // -------------------------------------------------------------------------

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const validationError = validate();

    if (validationError) {
      showError(validationError);
      return;
    }

    setIsLoading(true);

    try {
      await signup({
        name: name.trim(),
        contact: email.trim(),
        password,
      });

      // Successful signup enters the application through the dashboard.
      router.replace("/dashboard");
    } catch (err) {
      showError(
        err instanceof AuthApiError
          ? err.message
          : "Could not create account. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  }

  // -------------------------------------------------------------------------
  // Session restoration
  // -------------------------------------------------------------------------

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

  // -------------------------------------------------------------------------
  // UI
  // -------------------------------------------------------------------------

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Join NFL-EDGE and get the numbers before kickoff"
      footer={
        <>
          Already have an account?{" "}
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
          <Input
            label="Your name"
            name="name"
            type="text"
            autoComplete="name"
            placeholder="e.g. Alex Carter"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          <Input
            label="Email address"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <div>
            <PasswordField
              id="password"
              label="Password"
              placeholder="At least 8 characters"
              value={password}
              onChange={setPassword}
              show={showPassword}
              onToggle={() =>
                setShowPassword((value) => !value)
              }
            />

            {password.length > 0 && (
              <div className="mt-2">
                <div className="flex gap-1">
                  {[1, 2, 3, 4].map((level) => (
                    <div
                      key={level}
                      className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
                        level <= strength.score
                          ? strengthColors[strength.label]
                          : "bg-white/10"
                      }`}
                    />
                  ))}
                </div>

                <p className="mt-1 text-xs text-slate-400">
                  Password strength:{" "}
                  <span className="font-medium text-slate-200">
                    {strengthLabels[strength.label]}
                  </span>
                </p>
              </div>
            )}
          </div>

          <div>
            <PasswordField
              id="confirmPassword"
              label="Confirm password"
              placeholder="Re-enter your password"
              value={confirmPassword}
              onChange={setConfirmPassword}
              show={showConfirm}
              onToggle={() =>
                setShowConfirm((value) => !value)
              }
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
          loadingText="Creating account..."
          className="mt-6"
        >
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}