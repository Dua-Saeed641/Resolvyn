"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cx } from "@/lib/utils";

/** project.md §52: primary = white on black, secondary = dark, danger = red text/border only. */
const BTN = {
  primary: "bg-text-max text-black hover:bg-text-body",
  secondary: "border border-border bg-card-elevated text-text-primary hover:bg-border",
  danger: "border border-danger/50 bg-transparent text-danger hover:bg-danger/10",
  ghost: "text-text-muted hover:text-text-primary hover:bg-card",
} as const;

export function Button({
  variant = "secondary",
  size = "md",
  className,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof BTN; size?: "sm" | "md" }) {
  return (
    <button
      {...rest}
      className={cx(
        "inline-flex items-center justify-center gap-1.5 rounded font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-info",
        size === "sm" ? "px-2.5 py-1 text-xs" : "px-3.5 py-1.5 text-sm",
        BTN[variant],
        className,
      )}
    />
  );
}

export function Card({ title, subtitle, right, children, className, bodyClass }: {
  title?: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClass?: string;
}) {
  return (
    <section className={cx("rounded-lg border border-border bg-card", className)}>
      {(title || right) && (
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-2.5">
          <div className="min-w-0">
            {title && <h2 className="text-[13px] font-semibold text-text-primary">{title}</h2>}
            {subtitle && <p className="text-[11px] text-text-muted">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className={cx("p-4", bodyClass)}>{children}</div>
    </section>
  );
}

export const inputCls =
  "w-full rounded border border-border bg-bg-secondary px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary " +
  "focus:border-text-secondary focus:outline-none";

export function Label({ children }: { children: ReactNode }) {
  return <label className="mb-1 block text-[11px] uppercase tracking-wide text-text-muted">{children}</label>;
}

export function Kv({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1 text-[13px]">
      <dt className="shrink-0 text-text-muted">{label}</dt>
      <dd className="min-w-0 truncate text-right text-text-primary">{children}</dd>
    </div>
  );
}

export function ConfidenceIndicator({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="text-text-secondary">—</span>;
  const label = value >= 90 ? "High" : value >= 75 ? "Medium" : "Low";
  return (
    <span className="inline-flex items-center gap-2 text-[13px] tabular-nums text-text-primary">
      {value}%
      <span className="inline-block h-1 w-10 overflow-hidden rounded bg-border" aria-hidden>
        <span className="block h-full bg-text-body" style={{ width: `${value}%` }} />
      </span>
      <span className="text-xs text-text-muted">{label}</span>
    </span>
  );
}

export function AgentBadge({ name }: { name: string | null | undefined }) {
  if (!name) return <span className="text-text-secondary">Unassigned</span>;
  return <span className="rounded border border-border bg-card-elevated px-1.5 py-0.5 text-xs text-text-body">{name} Agent</span>;
}

export function Spinner({ className }: { className?: string }) {
  return <span className={cx("inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-text-secondary border-t-transparent", className)} aria-label="Loading" />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-pulse rounded bg-card-elevated", className)} />;
}
