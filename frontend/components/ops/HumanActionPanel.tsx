"use client";

import { useState } from "react";

import { ApprovalCard } from "@/components/ops/ApprovalCard";
import { Button, inputCls, Label } from "@/components/ui/primitives";
import type { TicketDetail } from "@/features/types";
import { api } from "@/lib/api";
import { DEPARTMENTS, HUMAN_ACTIONS, type HumanActionType } from "@/lib/constants";
import { cx, cn } from "@/lib/utils";

const HINT: Record<HumanActionType, string> = {
  GUIDE: "Add context the AI does not have. It is used on the live call right away.",
  APPROVE: "Gate a high-value action the AI has proposed.",
  CORRECT: "Fix an AI decision. Becomes guidance now and a rule for next time.",
  OVERRIDE: "Take control of this conversation. The AI stops replying.",
  TEACH: "Add a rule to the Solvable Rulebook for a department agent.",
};

/** The five human actions — always all five, always this order (docs/claude.md).
 *  Every button changes backend state; none is decorative (project.md §71). */
export function HumanActionPanel({ t }: { t: TicketDetail }) {
  const [open, setOpen] = useState<HumanActionType | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [f, setF] = useState({ guide: "", corrected: "", ai: "", reason: "", topic: "", knowledge: "", dept: t.assigned_agent ?? "Other", say: "", override: "" });
  const set = (k: keyof typeof f, v: string) => setF((p) => ({ ...p, [k]: v }));

  const pending = t.pending_actions.filter((a) => a.status === "PENDING");
  const taken = t.handled_by === "HUMAN";
  const resolved = t.status === "RESOLVED";

  const run = async (fn: () => Promise<unknown>, ok: string, reset?: () => void) => {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
      setMsg({ ok: true, text: ok });
      reset?.();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "Action failed" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="grid grid-cols-5 gap-1.5" role="group" aria-label="Human intelligence actions">
        {HUMAN_ACTIONS.map((a) => {
          const disabled = a === "APPROVE" && pending.length === 0;
          return (
            <button
              key={a}
              disabled={disabled}
              onClick={() => {
                setOpen(open === a ? null : a);
                setMsg(null);
              }}
              aria-pressed={open === a}
              title={disabled ? "No action is waiting for approval" : HINT[a]}
              className={cx(
                "rounded border px-1 py-1.5 text-[11px] font-semibold tracking-wide transition-colors disabled:cursor-not-allowed disabled:opacity-35",
                open === a ? "border-text-primary bg-primary text-primary-foreground" : "border-border bg-card-elevated text-text-primary hover:bg-border",
                a === "APPROVE" && pending.length > 0 && open !== a && "border-warning/60 text-warning",
              )}
            >
              {a}
              {a === "APPROVE" && pending.length > 0 ? ` · ${pending.length}` : ""}
            </button>
          );
        })}
      </div>

      <div className="mt-3 min-h-[24px]">
        {open === null && <p className="text-xs text-text-muted">Humans stay embedded in the loop. Pick an action.</p>}
        {open && <p className="mb-2 text-xs text-text-muted">{HINT[open]}</p>}

        {open === "GUIDE" && (
          <div className="space-y-2">
            <Label>Tell Resolvyn what it should consider</Label>
            <textarea className={cn(inputCls, "min-h-[64px]")} value={f.guide} onChange={(e) => set("guide", e.target.value)} placeholder="e.g. This customer is Premium: offer the fastest path and do not ask them to wait." />
            <Button variant="primary" size="sm" disabled={busy || !f.guide.trim()} onClick={() => run(() => api.post("/human-intelligence/guide", { ticket_id: t.ticket_id, text: f.guide }), "Guidance applied to the live AI.", () => set("guide", ""))}>
              Apply guidance
            </Button>
          </div>
        )}

        {open === "APPROVE" && (
          <div className="space-y-2">
            {pending.map((a) => (
              <ApprovalCard key={a.action_id} action={a} />
            ))}
          </div>
        )}

        {open === "CORRECT" && (
          <div className="space-y-2">
            <div>
              <Label>AI decision being corrected</Label>
              <input className={inputCls} value={f.ai} onChange={(e) => set("ai", e.target.value)} placeholder={t.next_step ?? "What the AI decided"} />
            </div>
            <div>
              <Label>Correct action</Label>
              <textarea className={cn(inputCls, "min-h-[56px]")} value={f.corrected} onChange={(e) => set("corrected", e.target.value)} placeholder="Refund only after duplicate transaction confirmation." />
            </div>
            <div>
              <Label>Reason (optional)</Label>
              <input className={inputCls} value={f.reason} onChange={(e) => set("reason", e.target.value)} />
            </div>
            <Button variant="primary" size="sm" disabled={busy || !f.corrected.trim()} onClick={() => run(() => api.post("/human-intelligence/correct", { ticket_id: t.ticket_id, correct_action: f.corrected, ai_decision: f.ai || null, reason: f.reason || null }), "Correction recorded. A learning signal and a rulebook entry were created.", () => setF((p) => ({ ...p, corrected: "", ai: "", reason: "" })))}>
              Submit correction
            </Button>
          </div>
        )}

        {open === "OVERRIDE" && (
          <div className="space-y-2">
            {!taken ? (
              <>
                <div>
                  <Label>What you will do instead</Label>
                  <input className={inputCls} value={f.override} onChange={(e) => set("override", e.target.value)} placeholder="Continue the shipment; the customer confirmed." />
                </div>
                <Button variant="danger" size="sm" disabled={busy} onClick={() => run(() => api.post("/human-intelligence/override", { ticket_id: t.ticket_id, decision: f.override, reason: "Human took control" }), "You now own this conversation. The AI has stopped replying.")}>
                  Override and take over
                </Button>
              </>
            ) : (
              <>
                <Label>Say to the caller{t.call_active ? "" : " (call has ended)"}</Label>
                <div className="flex gap-2">
                  <input className={inputCls} value={f.say} disabled={!t.call_active} onChange={(e) => set("say", e.target.value)} placeholder="Hi, this is Ananya from the team…" onKeyDown={(e) => e.key === "Enter" && f.say.trim() && run(() => api.post("/human-intelligence/say", { ticket_id: t.ticket_id, text: f.say }), "Sent.", () => set("say", ""))} />
                  <Button size="sm" disabled={busy || !f.say.trim() || !t.call_active} onClick={() => run(() => api.post("/human-intelligence/say", { ticket_id: t.ticket_id, text: f.say }), "Sent to the caller.", () => set("say", ""))}>
                    Send
                  </Button>
                </div>
                <Button variant="primary" size="sm" disabled={busy || resolved} onClick={() => run(() => api.post("/human-intelligence/resolve", { ticket_id: t.ticket_id, note: "Resolved by team member" }), "Ticket marked resolved.")}>
                  Mark resolved
                </Button>
              </>
            )}
          </div>
        )}

        {open === "TEACH" && (
          <div className="space-y-2">
            <div className="grid grid-cols-[1fr_130px] gap-2">
              <div>
                <Label>Topic</Label>
                <input className={inputCls} value={f.topic} onChange={(e) => set("topic", e.target.value)} placeholder="Refunds for duplicate transactions" />
              </div>
              <div>
                <Label>Department</Label>
                <select className={inputCls} value={f.dept} onChange={(e) => set("dept", e.target.value)}>
                  {DEPARTMENTS.map((d) => (
                    <option key={d}>{d}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <Label>Knowledge</Label>
              <textarea className={cn(inputCls, "min-h-[72px]")} value={f.knowledge} onChange={(e) => set("knowledge", e.target.value)} placeholder="If two successful transactions exist for the same order within 10 minutes, verify the duplicate before refunding." />
            </div>
            <Button variant="primary" size="sm" disabled={busy || !f.topic.trim() || !f.knowledge.trim()} onClick={() => run(() => api.post("/human-intelligence/teach", { topic: f.topic, knowledge: f.knowledge, department: f.dept, ticket_id: t.ticket_id }), "Saved to the Solvable Rulebook.", () => setF((p) => ({ ...p, topic: "", knowledge: "" })))}>
              Save knowledge
            </Button>
          </div>
        )}

        {msg && (
          <p role="status" className={cx("mt-2 text-xs", msg.ok ? "text-success" : "text-danger")}>
            {msg.ok ? "✓ " : "✕ "}
            {msg.text}
          </p>
        )}
      </div>
    </div>
  );
}
