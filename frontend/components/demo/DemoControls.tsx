"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";

/** project.md §46; spec §41: RUN DEMO replays PH-1042 live through the
 * backend state machine; RESET DEMO restores its default snapshot. Both
 * are real backend calls — realtime broadcasts (lib/realtime.tsx) drive
 * the UI update as each step actually happens. */
export function DemoControls() {
  const router = useRouter();
  const [busy, setBusy] = useState<"run" | "reset" | null>(null);

  async function run() {
    setBusy("run");
    try {
      await api.post("/demo/run");
    } finally {
      setBusy(null);
      router.refresh();
    }
  }

  async function reset() {
    setBusy("reset");
    try {
      await api.post("/demo/reset");
    } finally {
      setBusy(null);
      router.refresh();
    }
  }

  return (
    <div className="flex gap-2">
      <button
        onClick={run}
        disabled={busy !== null}
        className="rounded bg-text-primary px-3 py-1.5 text-xs font-medium text-bg-primary disabled:opacity-50"
      >
        {busy === "run" ? "Running…" : "▶ Run Demo"}
      </button>
      <button
        onClick={reset}
        disabled={busy !== null}
        className="rounded border border-border px-3 py-1.5 text-xs font-medium text-text-primary disabled:opacity-50"
      >
        Reset Demo
      </button>
    </div>
  );
}
