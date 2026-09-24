"use client";

import Link from "next/link";
import { useState } from "react";

import { Button, inputCls } from "@/components/ui/primitives";
import type { FirstTimeBug } from "@/features/types";
import { api } from "@/lib/api";
import { fmtClock } from "@/lib/format";

/**
 * memory-rulebook-detail.png: "A FIRST TIME BUG HAS BEEN REPORTED — HERE'S MORE DETAIL,
 * PLEASE ENTER YOUR SUGGESTION". The suggestion is written into the Solvable Rulebook and
 * handed to the AI, which continues the live call with it.
 */
export function FirstTimeBugCard({ bug, ticketId, compact = false }: { bug: FirstTimeBug; ticketId?: string; compact?: boolean }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const open = bug.status === "OPEN";

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/human-intelligence/bugs/${bug.bug_id}/suggest`, { suggestion: text });
      setText("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send the suggestion");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`animate-fade-in rounded-lg border ${open ? "border-danger/50 bg-danger/5" : "border-border bg-card"} p-4`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className={`text-[11px] font-semibold uppercase tracking-wide ${open ? "text-danger" : "text-text-muted"}`}>
            {open ? "A first time bug has been reported" : "First-time bug — suggestion recorded"}
          </p>
          <p className="mt-1 text-sm font-medium text-text-primary">{bug.title}</p>
        </div>
        <div className="shrink-0 text-right text-[11px] text-text-muted">
          <p>{bug.department} desk</p>
          <p>{fmtClock(bug.created_at)}</p>
        </div>
      </div>

      <p className="mt-2 text-xs text-text-muted">Here&apos;s more detail</p>
      <p className="mt-0.5 rounded border border-border bg-bg-secondary p-2 text-[13px] text-text-body">{bug.detail || "—"}</p>

      {open ? (
        <div className="mt-3">
          <label htmlFor={`sugg-${bug.bug_id}`} className="mb-1 block text-xs font-medium text-text-primary">
            Please enter your suggestion
          </label>
          <textarea
            id={`sugg-${bug.bug_id}`}
            className={`${inputCls} min-h-[72px]`}
            placeholder="What should the caller try? Resolvyn will use this on the live call and remember it for next time."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          {error && <p className="mt-1 text-xs text-danger">{error}</p>}
          <div className="mt-2 flex items-center justify-between">
            <p className="text-[11px] text-text-secondary">Added to the Solvable Rulebook + bug memory, then spoken to the caller.</p>
            <div className="flex gap-2">
              {!compact || !ticketId ? null : (
                <Link href={`/ops/tickets/${ticketId}`}>
                  <Button size="sm">Open ticket</Button>
                </Link>
              )}
              <Button variant="primary" size="sm" disabled={busy || !text.trim()} onClick={submit}>
                {busy ? "Sending…" : "Send to AI"}
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-3 border-t border-border pt-3">
          <p className="text-xs text-text-muted">Suggestion by {bug.suggested_by}</p>
          <p className="mt-0.5 text-[13px] text-text-primary">{bug.suggestion}</p>
        </div>
      )}
    </div>
  );
}
