import React from "react";
import { clsx } from "clsx";

export function Page(props: React.PropsWithChildren<{ title?: string }>) {
  return (
    <div className="min-h-dvh" style={{ background:"var(--color-bg)", color:"var(--color-text)" }}>
      <div className="max-w-6xl mx-auto p-6">
        {props.title && <h1 className="text-2xl font-semibold mb-6">{props.title}</h1>}
        {props.children}
      </div>
    </div>
  );
}

export function Card(props: React.PropsWithChildren<{ className?: string }>) {
  return (
    <div className={clsx("rounded-2xl p-5 transition-transform hover:-translate-y-0.5", props.className)}
         style={{ background:"var(--color-surface)", boxShadow:"var(--shadow)" }}>
      {props.children}
    </div>
  );
}

export function Button(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" }
){
  const { variant="primary", className, ...rest } = props;
  const base = "px-4 py-2 rounded-xl font-medium transition-colors inline-flex items-center gap-2 disabled:opacity-60";
  const styles = variant==="primary" ? { background:"var(--color-primary)", color:"var(--color-primary-contrast)" } : {};
  return <button className={clsx(base, className)} style={styles} {...rest} />;
}

export function Input(
  props: React.InputHTMLAttributes<HTMLInputElement> & { label?: string; hint?: string }
){
  const { label, hint, className, ...rest } = props;
  return (
    <label className="block space-y-2">
      {label && <span className="text-sm text-[var(--color-muted)]">{label}</span>}
      <input className={clsx(
          "w-full rounded-xl px-3 py-2 bg-transparent border outline-none",
          "border-white/10 focus:border-[var(--color-primary)]",
          className
        )}
        {...rest}
      />
      {hint && <span className="text-xs text-[var(--color-muted)]">{hint}</span>}
    </label>
  );
}
