"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

import { Button as ShButton } from "@/components/ui/button";
import { Card as ShCard, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton as ShSkeleton } from "@/components/ui/skeleton";
import { cn, cx } from "@/lib/utils";

/** App-level wrappers over shadcn/ui, kept so every screen shares one look: primary = filled, secondary = outline, danger = destructive outline. */
const VARIANT = { primary: "default", secondary: "outline", danger: "outline", ghost: "ghost" } as const;

export function Button({
  variant = "secondary",
  size = "md",
  className,
  ...rest
}: Omit<ButtonHTMLAttributes<HTMLButtonElement>, "size"> & { variant?: keyof typeof VARIANT; size?: "sm" | "md" }) {
  return (
    <ShButton
      {...rest}
      variant={VARIANT[variant]}
      size={size === "sm" ? "sm" : "default"}
      className={cn(variant === "danger" && "border-danger/40 text-danger hover:bg-danger/10 hover:text-danger", className)}
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
    <ShCard className={className}>
      {(title || right) && (
        <CardHeader className="flex-row items-center justify-between gap-3 space-y-0 border-b px-5 py-3.5">
          <div className="min-w-0 space-y-1">
            {title && <CardTitle>{title}</CardTitle>}
            {subtitle && <CardDescription>{subtitle}</CardDescription>}
          </div>
          {right}
        </CardHeader>
      )}
      <CardContent className={cn("p-5", bodyClass)}>{children}</CardContent>
    </ShCard>
  );
}

export const inputCls =
  "flex h-9 w-full rounded-md border border-input bg-card px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function Label({ children }: { children: ReactNode }) {
  return <label className="mb-1 block text-xs font-medium text-muted-foreground">{children}</label>;
}

export function Kv({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5 text-[13px]">
      <dt className="shrink-0 text-muted-foreground">{label}</dt>
      <dd className="min-w-0 truncate text-right font-medium text-foreground">{children}</dd>
    </div>
  );
}

export function ConfidenceIndicator({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="text-text-secondary">—</span>;
  const label = value >= 90 ? "High" : value >= 75 ? "Medium" : "Low";
  return (
    <span className="inline-flex items-center gap-2 text-[13px] tabular-nums text-foreground">
      {value}%
      <span className="inline-block h-1 w-10 overflow-hidden rounded bg-muted" aria-hidden>
        <span className="block h-full bg-primary/70" style={{ width: `${value}%` }} />
      </span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </span>
  );
}

export function AgentBadge({ name }: { name: string | null | undefined }) {
  if (!name) return <span className="text-text-secondary">Unassigned</span>;
  return <span className="rounded-md border bg-muted/60 px-1.5 py-0.5 text-xs text-foreground">{name} Agent</span>;
}

export function Spinner({ className }: { className?: string }) {
  return <span className={cx("inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent", className)} aria-label="Loading" />;
}

export function Skeleton({ className }: { className?: string }) {
  return <ShSkeleton className={className} />;
}
