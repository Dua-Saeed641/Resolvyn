"use client";

import { useState } from "react";

import type { AgentEvent } from "@/features/types";
import { Pill } from "@/components/ui/StatusBadge";
import { cx } from "@/lib/utils";

type Trace = {
  turn: number;
  heard: string;
  language: string;
  entities: Record<string, string | number>;
  filler?: string;
  filler_ms?: number;
  first_word_ms?: number;
  total_ms: number;
  jev?: { intent: string; department: string; confidence: number; sentiment: string; carried: boolean; source: string; query: string };
  jev_ms?: number;
  memory?: { best_rulebook: number; best_bug_memory: number; hits: { title: string; kind: string; score: number }[] };
  decision?: { path: string; reason: string; note: string | null };
  agent: string;
  tools: { tool: string; status: string }[];
  facts: string[];
  blocked: { said: string; why: string }[];
  said: string;
  llm: boolean;
  model?: string | null;
};

const PATH_TONE: Record<string, "success" | "info" | "warning" | "danger" | "muted"> = {
  INSTANT: "success",
  ACTION: "info",
  FIRST_TIME_BUG: "danger",
  KNOWN_OPEN_BUG: "warning",
  ESCALATED: "warning",
};

function ms(v?: number) {
  if (v == null) return "·";
  return v < 1000 ? `${v} ms` : `${(v / 1000).toFixed(1)} s`;
}

function Step({ n, label, time, children }: { n: number; label: string; time?: string; children: React.ReactNode }) {
  return (
    <li className="relative grid grid-cols-[22px_minmax(0,1fr)] gap-3 pb-3 last:pb-0">
      <span className="z-10 mt-0.5 flex h-[22px] w-[22px] items-center justify-center rounded-full border border-border bg-card text-[11px] text-text-muted">{n}</span>
      <div className="min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-[11px] font-medium uppercase tracking-wide text-text-muted">{label}</span>
          {time && <span className="font-mono text-[11px] text-text-muted">{time}</span>}
        </div>
        <div className="mt-0.5 text-[13px] leading-relaxed text-text-body">{children}</div>
      </div>
    </li>
  );
}

function TurnCard({ t, open, onToggle }: { t: Trace; open: boolean; onToggle: () => void }) {
  const ent = Object.entries(t.entities ?? {});
  const firstSound = t.filler_ms ?? t.first_word_ms;
  return (
    <div className="rounded-md border border-border">
      <button onClick={onToggle} className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-card-elevated" aria-expanded={open}>
        <span className="font-mono text-xs text-text-muted">#{t.turn}</span>
        <span className="min-w-0 flex-1 truncate text-[13px] text-text-primary">“{t.heard}”</span>
        {t.decision && <Pill tone={PATH_TONE[t.decision.path] ?? "muted"}>{t.decision.path.replace(/_/g, " ")}</Pill>}
        {t.blocked?.length > 0 && <Pill tone="warning">{t.blocked.length} blocked</Pill>}
        <span className="w-16 text-right font-mono text-xs text-text-muted" title="Time until the caller heard the first sound">{ms(firstSound)}</span>
      </button>
      {open && (
        <ol className="relative border-t border-border px-3 py-3 before:absolute before:bottom-4 before:left-[22px] before:top-4 before:w-px before:bg-border">
          <Step n={1} label="Heard" time={t.language === "hi" ? "Hindi / Hinglish" : "English"}>
            “{t.heard}”
            {ent.length > 0 && (
              <span className="mt-1 flex flex-wrap gap-1.5">
                {ent.map(([k, v]) => (
                  <Pill key={k}>{k.replace(/_/g, " ")}: {String(v)}</Pill>
                ))}
              </span>
            )}
          </Step>
          {t.filler && (
            <Step n={2} label="Instant acknowledgement (before any model ran)" time={ms(t.filler_ms)}>
              “{t.filler}”
            </Step>
          )}
          {t.jev && (
            <Step n={3} label={`Jev judgment · ${t.jev.source === "rules" ? "rules, no model" : "model-refined"}`} time={ms(t.jev_ms)}>
              {t.jev.intent} → <span className="text-text-primary">{t.jev.department} desk</span> · {t.jev.confidence}% · {t.jev.sentiment}
              {t.jev.carried && <span className="text-text-muted"> · kept from the previous turn</span>}
              <span className="mt-0.5 block text-xs text-text-muted">Memory query: {t.jev.query}</span>
            </Step>
          )}
          {t.memory && (
            <Step n={4} label="Memory recall" time={`rulebook ${t.memory.best_rulebook.toFixed(2)} · bugs ${t.memory.best_bug_memory.toFixed(2)}`}>
              {t.memory.hits.length === 0 ? (
                <span className="text-text-muted">Nothing relevant in memory.</span>
              ) : (
                <span className="flex flex-col gap-0.5">
                  {t.memory.hits.map((h, i) => (
                    <span key={i} className="flex justify-between gap-2">
                      <span className="truncate">{h.title}</span>
                      <span className="font-mono text-xs text-text-muted">{h.score.toFixed(2)}</span>
                    </span>
                  ))}
                </span>
              )}
            </Step>
          )}
          {t.decision && (
            <Step n={5} label="Decision engine">
              <span className="text-text-primary">{t.decision.path.replace(/_/g, " ")}</span>: {t.decision.reason}
              {t.decision.note && <span className="block text-xs text-text-muted">{t.decision.note}</span>}
            </Step>
          )}
          <Step n={6} label={`${t.agent} · tools`}>
            {t.tools.length === 0 ? (
              <span className="text-text-muted">No tools needed.</span>
            ) : (
              <span className="flex flex-wrap gap-1.5">
                {t.tools.map((x, i) => (
                  <Pill key={i} tone={x.status === "COMPLETED" ? "success" : x.status === "FAILED" ? "danger" : "muted"}>
                    {x.tool}
                  </Pill>
                ))}
              </span>
            )}
            {t.facts.length > 0 && (
              <ul className="mt-1.5 space-y-0.5 text-xs text-text-muted">
                {t.facts.map((f, i) => (
                  <li key={i}>✓ {f}</li>
                ))}
              </ul>
            )}
          </Step>
          <Step n={7} label="Truth guard">
            {t.blocked?.length ? (
              t.blocked.map((b, i) => (
                <span key={i} className="block">
                  <span className="text-warning">Blocked</span> “{b.said}” <span className="text-xs text-text-muted">({b.why})</span>
                </span>
              ))
            ) : (
              <span className="text-text-muted">Nothing unverified was said. Only the facts above can be stated.</span>
            )}
          </Step>
          <Step n={8} label={t.llm ? `Spoke · ${t.model ?? "language model"}, streamed sentence by sentence` : "Spoke · exact line (no model)"} time={`first word ${ms(t.first_word_ms)} · total ${ms(t.total_ms)}`}>
            “{t.said}”
          </Step>
        </ol>
      )}
    </div>
  );
}

/** The Live AI brain: every caller turn, from what was heard to what was said, with the reasoning and timings in between. */
export function BrainTrace({ events }: { events: AgentEvent[] }) {
  const traces = events
    .filter((e) => e.event_type === "TURN_TRACE" && e.meta?.trace)
    .map((e) => e.meta.trace as Trace)
    .sort((a, b) => b.turn - a.turn);
  const [openTurn, setOpenTurn] = useState<number | null>(null);
  if (traces.length === 0) {
    return <p className="text-sm text-text-muted">Each caller turn appears here as it happens: what was heard, how it was judged, what was recalled, the decision, the tools, and what the truth guard stopped.</p>;
  }
  const latest = traces[0].turn;
  const shown = openTurn ?? latest;
  const avg = Math.round(traces.reduce((s, t) => s + (t.filler_ms ?? t.first_word_ms ?? 0), 0) / traces.length);
  const blocked = traces.reduce((s, t) => s + (t.blocked?.length ?? 0), 0);
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-4 pb-1 text-xs text-text-muted">
        <span>
          <span className="font-mono text-text-primary">{traces.length}</span> turns
        </span>
        <span>
          avg first sound <span className={cx("font-mono", avg < 1500 ? "text-success" : "text-text-primary")}>{ms(avg)}</span>
        </span>
        <span>
          <span className="font-mono text-text-primary">{blocked}</span> unverified claims blocked
        </span>
      </div>
      {traces.map((t) => (
        <TurnCard key={t.turn} t={t} open={shown === t.turn} onToggle={() => setOpenTurn(shown === t.turn ? -1 : t.turn)} />
      ))}
    </div>
  );
}
