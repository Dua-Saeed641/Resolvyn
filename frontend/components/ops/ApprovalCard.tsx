"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/primitives";
import { Pill } from "@/components/ui/StatusBadge";
import type { PendingAction } from "@/features/types";
import { api } from "@/lib/api";
import { money } from "@/lib/format";

/** project.md §24: ACTION REQUIRES APPROVAL — amount, reason, policy, then APPROVE / REJECT. */
export function ApprovalCard({ action, showLink = false }: { action: PendingAction; showLink?: boolean }) {
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pending = action.status === "PENDING";

  const decide = async (kind: "approve" | "reject") => {
    setBusy(kind);
    setError(null);
    try {
      await api.post(`/human-intelligence/${kind}`, {
        ticket_id: action.ticket_id,
        action_id: action.action_id,
        reason: kind === "approve" ? "Duplicate transaction verified" : "Rejected by operator",
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className={`animate-fade-in rounded-lg border p-4 ${pending ? "border-warning/50 bg-warning/5" : "border-border bg-card"}`}>
      <div className="flex items-start justify-between gap-3">
        <p className={`text-[11px] font-semibold uppercase tracking-wide ${pending ? "text-warning" : "text-text-muted"}`}>
          {pending ? "Action requires approval" : `Action ${action.status.toLowerCase()}`}
        </p>
        {showLink && (
          <Link href={`/ops/tickets/${action.ticket_id}`} className="text-xs text-text-muted underline underline-offset-2 hover:text-text-primary">
            {action.ticket_id}
          </Link>
        )}
      </div>
      <p className="mt-1 text-sm font-medium capitalize text-text-primary">{action.action_type}</p>
      <dl className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-[13px]">
        <dt className="text-text-muted">Amount</dt>
        <dd className="text-right tabular-nums text-text-primary">{action.params.amount != null ? money(action.params.amount) : "—"}</dd>
        <dt className="text-text-muted">Order</dt>
        <dd className="text-right text-text-primary">{action.params.order_id ?? "—"}</dd>
        <dt className="text-text-muted">Reason</dt>
        <dd className="text-right text-text-primary">{action.params.reason ?? "—"}</dd>
        <dt className="text-text-muted">Policy</dt>
        <dd className="text-right text-text-primary">{action.policy}</dd>
        <dt className="text-text-muted">Risk</dt>
        <dd className="text-right">
          <Pill tone="warning">{action.risk}</Pill>
        </dd>
      </dl>
      {error && <p className="mt-2 text-xs text-danger">{error}</p>}
      {pending ? (
        <div className="mt-3 flex gap-2">
          <Button variant="primary" disabled={busy !== null} onClick={() => decide("approve")}>
            {busy === "approve" ? "Approving…" : "Approve"}
          </Button>
          <Button variant="danger" disabled={busy !== null} onClick={() => decide("reject")}>
            Reject
          </Button>
        </div>
      ) : (
        <p className="mt-2 text-xs text-text-muted">Decided by {action.decided_by ?? "—"}</p>
      )}
    </div>
  );
}
