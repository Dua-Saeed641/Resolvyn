"use client";

import { useRealtime } from "@/lib/realtime";
import { cx } from "@/lib/utils";

/** project.md §11: subtle system status, no neon "AI ONLINE" effect. */
export function SystemStatus() {
  const { connected } = useRealtime();
  return (
    <span className="flex items-center gap-1.5">
      <span className={cx("h-1.5 w-1.5 rounded-full", connected ? "bg-success" : "bg-text-muted")} aria-hidden />
      {connected ? "Operational" : "Reconnecting"}
    </span>
  );
}
