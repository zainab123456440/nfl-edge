import React from "react";

type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
};

export default function Input({
  label,
  error,
  id,
  className = "",
  ...props
}: InputProps) {
  const inputId = id || props.name;
  const errorId = inputId ? `${inputId}-error` : undefined;

  return (
    <div className="w-full">
      {label && (
        <label
          htmlFor={inputId}
          className="mb-1.5 block text-sm font-medium text-slate-300"
        >
          {label}
        </label>
      )}

      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        {...props}
        className={`w-full rounded-xl border bg-slate-950/70 px-4 py-3 text-sm text-white shadow-inner shadow-black/20 outline-none transition placeholder:text-slate-600 focus:ring-2 disabled:cursor-not-allowed disabled:opacity-50 ${
          error
            ? "border-red-500/60 focus:border-red-500 focus:ring-red-500/20"
            : "border-slate-700 hover:border-slate-600 focus:border-blue-500 focus:ring-blue-500/25"
        } ${className}`}
      />

      {error && (
        <p id={errorId} className="mt-1 text-xs text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}