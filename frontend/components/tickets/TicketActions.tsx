"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Modal } from "@/components/ui/Modal";
import type { HumanActionType } from "@/lib/constants";
import { HUMAN_ACTION_LABELS } from "@/lib/constants";
import { api } from "@/lib/api";

/**
 * spec §11, §23-28: the five human-intelligence actions, always visible as
 * distinct buttons (never collapsed into a single "Escalate"). Each one
 * posts straight to backend/app/api/routes/human_intelligence.py and lets
 * the realtime layer (lib/realtime.tsx) refresh the page with real state.
 */
export function TicketActions({
  ticketId,
  intent,
  pendingAction,
  confidence,
  canGuide,
  canApprove,
  canCorrectOrOverride,
  isFirstTimeBug,
}: {
  ticketId: string;
  intent: string | null;
  pendingAction: string | null;
  confidence: number | null;
  canGuide: boolean;
  canApprove: boolean;
  canCorrectOrOverride: boolean;
  isFirstTimeBug: boolean;
}) {
  const router = useRouter();
  const [open, setOpen] = useState<HumanActionType | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [guidance, setGuidance] = useState("");
  const [correction, setCorrection] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [teachTopic, setTeachTopic] = useState("");
  const [teachKnowledge, setTeachKnowledge] = useState("");

  const operator = "Operator 01";

  async function submit(path: string, body: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/human-intelligence/${path}`, { ticket_id: ticketId, operator, ...body });
      setOpen(null);
      router.refresh();
    } catch {
      setError("That action couldn't be completed — check the ticket is in the right state.");
    } finally {
      setBusy(false);
    }
  }

  const buttons: { type: HumanActionType; show: boolean; danger?: boolean }[] = [
    { type: "GUIDE", show: canGuide },
    { type: "APPROVE", show: canApprove },
    { type: "CORRECT", show: canCorrectOrOverride },
    { type: "OVERRIDE", show: canCorrectOrOverride, danger: true },
    { type: "TEACH", show: isFirstTimeBug },
  ];

  return (
    <>
      <div className="flex flex-wrap gap-2">
        {buttons
          .filter((b) => b.show)
          .map((b) => (
            <button
              key={b.type}
              onClick={() => setOpen(b.type)}
              className={
                b.type === "APPROVE"
                  ? "rounded bg-text-primary px-3 py-1.5 text-xs font-medium text-bg-primary"
                  : b.danger
                    ? "rounded border border-danger/40 px-3 py-1.5 text-xs font-medium text-danger"
                    : "rounded border border-border px-3 py-1.5 text-xs font-medium text-text-primary hover:border-text-muted"
              }
            >
              {HUMAN_ACTION_LABELS[b.type]}
            </button>
          ))}
      </div>

      {open === "GUIDE" && (
        <Modal title="Guide Resolvyn" onClose={() => setOpen(null)}>
          <p className="text-xs text-text-muted">Current AI interpretation: {intent ?? "Unclassified"}</p>
          <textarea
            value={guidance}
            onChange={(e) => setGuidance(e.target.value)}
            rows={3}
            placeholder="Tell Resolvyn what it should consider..."
            className="mt-3 w-full rounded border border-border bg-bg-primary p-2 text-sm text-text-primary"
          />
          {error && <p className="mt-2 text-xs text-danger">{error}</p>}
          <button
            disabled={busy || !guidance.trim()}
            onClick={() => submit("guide", { guidance })}
            className="mt-3 rounded bg-text-primary px-3 py-1.5 text-xs font-medium text-bg-primary disabled:opacity-50"
          >
            Apply guidance
          </button>
        </Modal>
      )}

      {open === "APPROVE" && (
        <Modal title="Action requires human approval" onClose={() => setOpen(null)}>
          <dl className="grid grid-cols-2 gap-y-2 text-xs">
            <dt className="text-text-muted">Action</dt>
            <dd className="text-text-primary">{pendingAction?.replaceAll("_", " ") ?? "Pending action"}</dd>
            <dt className="text-text-muted">Confidence</dt>
            <dd className="text-text-primary">{confidence != null ? `${confidence}%` : "—"}</dd>
          </dl>
          {error && <p className="mt-2 text-xs text-danger">{error}</p>}
          <div className="mt-4 flex gap-2">
            <button
              disabled={busy}
              onClick={() => submit("approve", {})}
              className="rounded bg-text-primary px-3 py-1.5 text-xs font-medium text-bg-primary disabled:opacity-50"
            >
              Approve
            </button>
            <button onClick={() => setOpen(null)} className="rounded border border-border px-3 py-1.5 text-xs font-medium text-text-primary">
              Cancel
            </button>
          </div>
        </Modal>
      )}

      {open === "CORRECT" && (
        <Modal title="Correct AI decision" onClose={() => setOpen(null)}>
          <p className="text-xs text-text-muted">AI decision: {intent ?? "—"}</p>
          <textarea
            value={correction}
            onChange={(e) => setCorrection(e.target.value)}
            rows={3}
            placeholder="Correct action..."
            className="mt-3 w-full rounded border border-border bg-bg-primary p-2 text-sm text-text-primary"
          />
          {error && <p className="mt-2 text-xs text-danger">{error}</p>}
          <button
            disabled={busy || !correction.trim()}
            onClick={() => submit("correct", { correction })}
            className="mt-3 rounded bg-text-primary px-3 py-1.5 text-xs font-medium text-bg-primary disabled:opacity-50"
          >
            Submit correction
          </button>
        </Modal>
      )}

      {open === "OVERRIDE" && (
        <Modal title="Override current action" onClose={() => setOpen(null)}>
          <p className="text-xs text-text-muted">This takes direct control of ticket {ticketId}.</p>
          <textarea
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
            rows={3}
            placeholder="Reason for override..."
            className="mt-3 w-full rounded border border-border bg-bg-primary p-2 text-sm text-text-primary"
          />
          {error && <p className="mt-2 text-xs text-danger">{error}</p>}
          <button
            disabled={busy || !overrideReason.trim()}
            onClick={() => submit("override", { reason: overrideReason })}
            className="mt-3 rounded border border-danger/40 px-3 py-1.5 text-xs font-medium text-danger disabled:opacity-50"
          >
            Confirm override
          </button>
        </Modal>
      )}

      {open === "TEACH" && (
        <Modal title="Teach Resolvyn" onClose={() => setOpen(null)}>
          <label className="text-xs text-text-muted">Topic</label>
          <input
            value={teachTopic}
            onChange={(e) => setTeachTopic(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-bg-primary p-2 text-sm text-text-primary"
          />
          <label className="mt-3 block text-xs text-text-muted">Knowledge / resolution</label>
          <textarea
            value={teachKnowledge}
            onChange={(e) => setTeachKnowledge(e.target.value)}
            rows={3}
            className="mt-1 w-full rounded border border-border bg-bg-primary p-2 text-sm text-text-primary"
          />
          {error && <p className="mt-2 text-xs text-danger">{error}</p>}
          <button
            disabled={busy || !teachTopic.trim() || !teachKnowledge.trim()}
            onClick={() => submit("teach", { topic: teachTopic, knowledge: teachKnowledge })}
            className="mt-3 rounded bg-text-primary px-3 py-1.5 text-xs font-medium text-bg-primary disabled:opacity-50"
          >
            Save knowledge
          </button>
        </Modal>
      )}
    </>
  );
}
