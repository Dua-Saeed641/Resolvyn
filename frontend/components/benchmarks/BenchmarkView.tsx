"use client";

import { Check, Cpu, Gauge, GraduationCap, Mail, ShieldCheck, Sparkles, Target, X } from "lucide-react";
import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type Results = Record<string, any>;

const pct = (x: number, d = 0) => `${(x * 100).toFixed(d)}%`;
const secs = (ms: number) => `${(ms / 1000).toFixed(1)} s`;
const frac = (s: string) => {
  const [a, b] = s.split("/").map(Number);
  return { a, b, r: b ? a / b : 0 };
};

/* ── small building blocks ─────────────────────────────────────────────────────────────────────────────────────────── */

function Section({ icon: Icon, title, kicker, children }: { icon: typeof Check; title: string; kicker: string; children: ReactNode }) {
  return (
    <section className="space-y-4">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border bg-card text-brand">
          <Icon className="h-[18px] w-[18px]" />
        </span>
        <div>
          <h2 className="font-display text-xl tracking-tight text-foreground">{title}</h2>
          <p className="mt-0.5 max-w-3xl text-sm text-muted-foreground">{kicker}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function Bar({ value, tone = "brand", label, right, thin }: { value: number; tone?: "brand" | "danger" | "muted" | "warning"; label?: string; right?: string; thin?: boolean }) {
  const fill = { brand: "bg-brand", danger: "bg-danger", muted: "bg-muted-foreground/50", warning: "bg-warning" }[tone];
  return (
    <div className="flex items-center gap-3 text-sm">
      {label ? <span className="w-44 shrink-0 text-muted-foreground">{label}</span> : null}
      <div className={cn("flex-1 overflow-hidden rounded-full bg-border/70", thin ? "h-1.5" : "h-2.5")}>
        <div className={cn("h-full rounded-full transition-[width] duration-700", fill)} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
      </div>
      {right ? <span className="w-24 shrink-0 text-right font-medium tabular-nums text-foreground">{right}</span> : null}
    </div>
  );
}

function Big({ value, unit, label, sub, accent }: { value: string; unit?: string; label: string; sub?: string; accent?: boolean }) {
  return (
    <Card className={cn("relative overflow-hidden px-5 py-4", accent && "border-brand/40")}>
      {accent ? <div className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full bg-brand/15 blur-2xl" /> : null}
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-2 flex items-baseline gap-1.5 font-display text-[40px] font-normal leading-none tracking-tight text-foreground tabular-nums">
        {value}
        {unit ? <span className="text-base text-muted-foreground">{unit}</span> : null}
      </p>
      {sub ? <p className="mt-2 text-xs text-muted-foreground">{sub}</p> : null}
    </Card>
  );
}

function Chip({ ok, children }: { ok: boolean; children: ReactNode }) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium", ok ? "border-success/30 bg-success/10 text-success" : "border-danger/30 bg-danger/10 text-danger")}>
      {ok ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
      {children}
    </span>
  );
}

const say = (s: string) => s.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

/* ── the truth gate ────────────────────────────────────────────────────────────────────────────────────────────────── */

function truthNumbers(t: Results | undefined) {
  if (!t?.per_mode?.stress_raw) return null;
  const m = t.per_mode;
  const stress = { raw: m.stress_raw, guarded: m.stress_guarded };
  const normal = { raw: m.raw, guarded: m.guarded };
  const sum = (k: "probes" | "violations" | "blocked" | "would_block", modes: string[]) => modes.reduce((n, x) => n + (m[x]?.[k] ?? 0), 0);
  const gated = ["guarded", "stress_guarded"], alone = ["raw", "stress_raw"];
  return {
    m, stress, normal,
    total: { probes: sum("probes", gated), gatedBad: sum("violations", gated), aloneBad: sum("violations", alone), stopped: sum("blocked", gated), wouldStop: sum("would_block", alone), aloneProbes: sum("probes", alone) },
  };
}

function TruthGate({ t }: { t: Results | undefined }) {
  const n = truthNumbers(t);
  if (!n || !t) {
    return (
      <Card className="p-6 text-sm text-muted-foreground">
        The live adversarial run has not been recorded yet. Run <code className="rounded bg-muted px-1.5 py-0.5">python -m benchmarks.run --sections truth</code>.
      </Card>
    );
  }
  const rows: { title: string; note: string; raw: any; guarded: any }[] = [
    { title: "Stress test", note: "The rules are stripped from the model's prompt, so the guard is the only defence.", raw: n.stress.raw, guarded: n.stress.guarded },
    { title: "Normal operation", note: "Prompt rules on, as shipped. The guard is a second line of defence.", raw: n.normal.raw, guarded: n.normal.guarded },
  ];
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        {rows.map((r) => (
          <Card key={r.title} className="space-y-4 p-5">
            <div>
              <p className="text-sm font-medium text-foreground">{r.title}</p>
              <p className="text-xs text-muted-foreground">{r.note}</p>
            </div>
            <Bar label="Model alone" tone="muted" value={1 - r.raw.violation_rate} right={`${r.raw.probes - r.raw.violations}/${r.raw.probes} truthful`} />
            <Bar label="With the truth gate" tone="brand" value={1 - r.guarded.violation_rate} right={`${r.guarded.probes - r.guarded.violations}/${r.guarded.probes} truthful`} />
            <div className="flex flex-wrap items-center gap-x-5 gap-y-1 border-t pt-3 text-xs text-muted-foreground">
              <span>
                Sentences the gate stopped: <b className="text-foreground">{r.guarded.blocked}</b>
              </span>
              <span>
                Turns where the gate would step in: <b className="text-foreground">{r.raw.would_block}</b> of {r.raw.probes}
              </span>
              <span>
                Still helpful: <b className="text-foreground">{pct(r.guarded.completeness)}</b>
              </span>
            </div>
          </Card>
        ))}
      </div>

      <Card className="overflow-hidden">
        <div className="grid grid-cols-[1.6fr_repeat(4,minmax(0,1fr))] gap-2 border-b bg-muted/40 px-4 py-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          <span>What the model is tempted to invent</span>
          <span className="text-center">Stress: alone</span>
          <span className="text-center">Stress: gated</span>
          <span className="text-center">Normal: alone</span>
          <span className="text-center">Normal: gated</span>
        </div>
        {Object.entries<any>(t.per_scenario).map(([k, v]) => (
          <div key={k} className="grid grid-cols-[1.6fr_repeat(4,minmax(0,1fr))] items-center gap-2 border-b px-4 py-2 text-sm last:border-0">
            <span className="text-foreground">{say(k)}</span>
            {(["stress_raw", "stress_guarded", "raw", "guarded"] as const).map((mode) => {
              const f = frac(v[mode] ?? "0/0");
              const gated = mode.includes("guarded");
              return (
                <span key={mode} className="text-center">
                  <span className={cn("inline-block min-w-[3rem] rounded-md px-2 py-0.5 text-xs font-medium tabular-nums", f.a === 0 ? "bg-success/10 text-success" : gated ? "bg-warning/15 text-warning" : "bg-danger/10 text-danger")}>{v[mode] ?? "—"}</span>
                </span>
              );
            })}
          </div>
        ))}
      </Card>

      <p className="text-xs text-muted-foreground">
        Honest reading: with the rules in its prompt and verified facts handed to it, the 4B model is already truthful nearly every time. The gate is the safety net for the rare slip, and it costs a little helpfulness because it drops a sentence it cannot verify. Small sample ({n.total.probes + n.total.aloneProbes} conversations), so read the shape, not the decimals.
      </p>

      {t.examples?.filter((e: any) => e.mode.endsWith("raw")).length ? (
        <Card className="space-y-2 p-5">
          <p className="text-sm font-medium text-foreground">What the ungated model actually said</p>
          {t.examples
            .filter((e: any) => e.mode.endsWith("raw"))
            .slice(0, 3)
            .map((e: any, i: number) => (
              <p key={i} className="rounded-md border border-danger/20 bg-danger/5 px-3 py-2 text-sm text-foreground">
                <span className="mr-2 text-[11px] font-medium uppercase tracking-wider text-danger">{say(e.scenario)}</span>“{e.said}”
              </p>
            ))}
        </Card>
      ) : null}
    </div>
  );
}

/* ── the page ──────────────────────────────────────────────────────────────────────────────────────────────────────── */

export function BenchmarkView({ r }: { r: Results }) {
  const res = r.resolution, lrn = r.learning, off = r.offline ?? {}, jev = off.jev ?? {}, ho = jev.heldout ?? {}, ret = off.retrieval ?? {};
  const jm = r.jev_model, em = r.email, srv = r.server_side, lat = r.latency, eng = r.engine, gpu = r.gpu_loaded;
  const truth = truthNumbers(r.truth);
  const relay = lrn ? [...lrn.rows.map((x: any) => x.relay_first_word_ms)].sort((a: number, b: number) => a - b)[Math.floor(lrn.rows.length / 2)] : 0;

  return (
    <div className="mx-auto max-w-[1180px] space-y-12 pb-16">
      {/* headline */}
      <header className="relative overflow-hidden rounded-2xl border bg-card px-7 py-8">
        <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-brand/15 blur-3xl" />
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-brand">Measured, not claimed</p>
        <h1 className="mt-2 max-w-3xl font-display text-[34px] leading-[1.1] tracking-tight text-foreground">
          Every answer is verified before it is said.
        </h1>
        <p className="mt-3 max-w-2xl text-sm text-muted-foreground">
          Every number on this page comes from real conversations against the running system with a {String(r.model).split(",")[0]} model on a {gpu?.vram_total_mb ? Math.round(gpu.vram_total_mb / 1024) : 4} GB laptop GPU. No cloud model, no API keys.
        </p>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Big accent label="Everyday support cases solved" value={`${res.passed} of ${res.n}`} sub="start to finish; money moves only after a manager approves" />
          <Big accent label="Replies that stayed truthful" value={truth ? `${Math.round((1 - truth.total.gatedBad / truth.total.probes) * 100)}%` : "—"} sub={truth ? `across ${truth.total.probes} conversations built to make it invent things` : "run the adversarial test"} />
          <Big accent label="New problems learned from one tip" value={`${Math.round(lrn.second_caller_from_memory * lrn.n)} of ${lrn.n}`} sub={`the live caller heard the fix ${secs(relay)} after the manager sent it`} />
          <Big accent label="Until Riya starts answering" value={secs(srv?.first_word_ms?.p50 ?? 0)} sub="median, on a 4 GB laptop GPU" />
        </div>
      </header>

      {/* how it works, one strip */}
      <div className="grid gap-2 sm:grid-cols-4">
        {[
          ["Jev decides", "Rules read the caller in 0.4 ms. No model needed for the obvious."],
          ["Tools verify", "Orders, payments and refunds are looked up, never remembered."],
          ["Model phrases", "It may only put verified facts into words."],
          ["Truth gate", "Any sentence with an unverified date, amount, ID or “it’s done” is dropped."],
        ].map(([h, d], i) => (
          <Card key={h} className="px-4 py-3">
            <p className="text-xs font-medium text-brand">Step {i + 1}</p>
            <p className="mt-1 text-sm font-medium text-foreground">{h}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{d}</p>
          </Card>
        ))}
      </div>

      <Section icon={ShieldCheck} title="The truth gate" kicker="We deliberately tempt the model to invent: a delivery date that does not exist, a finished refund that is still pending, “other customers reported this”, a price, a warranty, a call-back time. Each reply is judged against a ground-truth pattern that is independent of the gate's own rules.">
        <TruthGate t={r.truth} />
      </Section>

      <Section icon={Target} title="Resolution with the human gates held" kicker="Twelve end-to-end scenarios, judged by tool calls, ticket state and what the customer actually heard.">
        <Card className="overflow-hidden">
          <div className="grid divide-y sm:grid-cols-2 sm:divide-y-0">
            {res.scenarios.map((s: any, i: number) => (
              <div key={s.id} className={cn("flex items-center justify-between gap-3 px-4 py-2.5 text-sm", i % 2 === 0 && "sm:border-r", i >= 2 && "sm:border-t")}>
                <span className="text-foreground">{say(s.id)}</span>
                <span className="flex items-center gap-3">
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {s.turns} turn{s.turns === 1 ? "" : "s"} · {s.seconds.toFixed(0)} s{s.human_actions ? ` · ${s.human_actions} human` : ""}
                  </span>
                  <Chip ok={s.passed}>{s.passed ? "Pass" : "Fail"}</Chip>
                </span>
              </div>
            ))}
          </div>
        </Card>
      </Section>

      <Section icon={GraduationCap} title="A first-time problem becomes the answer for the next customer" kicker="Three faults the system had never seen. It flags each to a manager instead of guessing. One typed suggestion is relayed on the live call, then a different caller with different wording is answered from memory.">
        <div className="grid gap-3 lg:grid-cols-3">
          {lrn.rows.map((x: any) => (
            <Card key={x.issue} className="space-y-3 p-4">
              <p className="text-sm font-medium text-foreground">“{x.issue.trim()}…”</p>
              {[
                ["Flagged, not guessed", x.flagged_for_manager, ""],
                ["Fix relayed live", x.suggestion_relayed_live, x.relay_first_word_ms ? `${secs(x.relay_first_word_ms)} after send` : ""],
                ["Next caller, from memory", x.second_caller_answered_from_memory, x.second_caller_first_word_ms ? secs(x.second_caller_first_word_ms) : ""],
              ].map(([l, ok, t]) => (
                <div key={l as string} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{l as string}</span>
                  <span className="flex items-center gap-2">
                    {t ? <span className="text-xs tabular-nums text-muted-foreground">{t as string}</span> : null}
                    <Chip ok={ok as boolean}>{ok ? "Yes" : "No"}</Chip>
                  </span>
                </div>
              ))}
            </Card>
          ))}
        </div>
      </Section>

      <Section icon={Sparkles} title="Understanding, on sentences it was never tuned on" kicker="A dev set the phrase lists were tuned against, and a held-out set written afterwards. The held-out numbers are the honest ones.">
        <Card className="space-y-3.5 p-5">
          <Bar label="Route to department, rules only" value={ho.routing?.department_accuracy ?? 0} tone="warning" right={pct(ho.routing?.department_accuracy ?? 0)} />
          {jm ? <Bar label="…plus 4B model when unsure" value={jm.with_model_help} right={pct(jm.with_model_help, 1)} /> : null}
          <Bar label="“I want a person”, recall" value={ho.human_request?.recall ?? 0} right={pct(ho.human_request?.recall ?? 0)} />
          <Bar label="“I want a person”, precision" value={ho.human_request?.precision ?? 0} right={pct(ho.human_request?.precision ?? 0)} />
          <Bar label="Side talk vs. addressed to us" value={jev.side_talk?.accuracy ?? 0} right={pct(jev.side_talk?.accuracy ?? 0)} />
          <Bar label="Right document, first result" value={ret.hit_at_1 ?? 0} right={pct(ret.hit_at_1 ?? 0)} />
          <Bar label="Right document, top three" value={ret.hit_at_3 ?? 0} right={pct(ret.hit_at_3 ?? 0)} />
          {jm ? (
            <p className="border-t pt-3 text-xs text-muted-foreground">
              Rules alone score {pct(ho.routing?.department_accuracy ?? 0)} on unseen sentences; the model is consulted on {pct(jm.asked_model)} of them, which lifts it to {pct(jm.with_model_help, 1)}. We show both so the number is not a black box.
            </p>
          ) : null}
        </Card>
      </Section>

      <div className="grid gap-8 lg:grid-cols-2">
        <Section icon={Gauge} title="Speed" kicker="Median and 95th percentile, what a caller experiences.">
          <Card className="space-y-3.5 p-5">
            {[
              ["Spoken acknowledgement", srv?.acknowledgement_ms],
              ["First real word", srv?.first_word_ms],
              ["Complete turn, tools included", srv?.turn_total_ms],
            ].map(([l, m]: any) =>
              m ? (
                <div key={l}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="text-muted-foreground">{l}</span>
                    <span className="tabular-nums text-foreground">
                      {m.p50 < 100 ? `${m.p50} ms` : secs(m.p50)} <span className="text-xs text-muted-foreground">· p95 {m.p95 < 100 ? `${m.p95} ms` : secs(m.p95)}</span>
                    </span>
                  </div>
                  <Bar thin value={Math.min(1, m.p50 / 5000)} />
                </div>
              ) : null,
            )}
            <p className="border-t pt-3 text-xs text-muted-foreground">
              Jev judges a sentence in {jev.speed?.p50_ms?.toFixed(1)} ms ({jev.speed?.sentences?.toLocaleString()} sentences timed). Generation runs at {eng?.tokens_per_second} tokens/s.
            </p>
          </Card>
        </Section>

        <Section icon={Cpu} title="What it costs to run" kicker="The whole live conversation runs on one laptop.">
          <Card className="space-y-4 p-5">
            <div>
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-muted-foreground">GPU memory, model loaded</span>
                <span className="tabular-nums text-foreground">{(gpu?.vram_used_mb / 1024).toFixed(1)} of {Math.round(gpu?.vram_total_mb / 1024)} GB</span>
              </div>
              <Bar thin value={gpu ? gpu.vram_used_mb / gpu.vram_total_mb : 0} />
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                ["Cloud model calls", "0"],
                ["Per-minute fees", "$0"],
                ["Server ready", `${r.server?.ready_seconds} s`],
                ["Automated tests", `${(r.tests?.backend ?? 0) + (r.tests?.agents ?? 0)} passing`],
              ].map(([k, v]) => (
                <div key={k} className="rounded-lg border bg-muted/30 px-3 py-2">
                  <p className="text-xs text-muted-foreground">{k}</p>
                  <p className="font-display text-lg text-foreground">{v}</p>
                </div>
              ))}
            </div>
          </Card>
        </Section>
      </div>

      {em ? (
        <Section icon={Mail} title="The email after every call" kicker="A short summary built only from verified records, never from the model's memory of the call.">
          <Card className="grid gap-4 p-5 sm:grid-cols-3">
            <div>
              <p className="font-display text-3xl text-foreground">{em.specifics_grounded}/{em.specifics_checked}</p>
              <p className="text-xs text-muted-foreground">order, refund and payment IDs and amounts that trace back to the ticket</p>
            </div>
            <div>
              <p className="font-display text-3xl text-foreground">{r.email_tests?.passed ?? "—"}</p>
              <p className="text-xs text-muted-foreground">protocol, threading, loop-guard and safety tests passing</p>
            </div>
            <div>
              <p className="font-display text-3xl text-foreground">{((em.max_message_bytes ?? 0) / 1024).toFixed(0)} KB</p>
              <p className="text-xs text-muted-foreground">largest message; Gmail clips at 102 KB</p>
            </div>
          </Card>
        </Section>
      ) : null}

      <footer className="border-t pt-5 text-xs text-muted-foreground">
        <p>
          {r.hardware?.gpu?.name} · {r.hardware?.cpu} · {r.hardware?.ram_gb} GB RAM · measured {r.when}. Customer, order, payment and refund systems are simulations, so “verified” means verified against those services; the mechanism is what is measured. Samples are small and callers are scripted, so treat percentages as measurements of this build, not population statistics. Method and limits: docs/benchmarks.md.
        </p>
      </footer>
    </div>
  );
}
