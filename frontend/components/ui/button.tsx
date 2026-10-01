import React from "react";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
  /** Text shown next to the spinner while loading, e.g. "Signing in..." */
  loadingText?: string;
};

export default function Button({
  children,
  variant = "primary",
  size = "md",
  isLoading = false,
  loadingText = "Please wait...",
  disabled,
  className = "",
  ...props
}: ButtonProps) {
  const variants = {
    primary:
      "bg-gradient-to-b from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-600/25 hover:from-blue-400 hover:to-blue-500 focus:ring-blue-500/40",
    secondary:
      "border border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800 focus:ring-slate-500/30",
  };

  const sizes = {
    sm: "h-9 px-3 text-sm",
    md: "h-10 px-4 text-sm",
    lg: "h-12 px-5 text-base",
  };

  return (
    <button
      {...props}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      className={`inline-flex w-full items-center justify-center rounded-xl font-semibold transition-all duration-200 focus:outline-none focus:ring-2 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {isLoading ? (
        <>
          <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
          {loadingText}
        </>
      ) : (
        children
      )}
    </button>
  );
}