import { ArrowRight, Brain, Ear, GraduationCap, Hand, Headphones, Mail, MessageSquare, Phone, ShieldCheck, Sparkles, Wrench, type LucideIcon } from "lucide-react";
import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import { Aura } from "@/components/brand/Aura";
import { Logo, LogoMark } from "@/components/brand/Logo";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "How Resolvyn works",
  description: "What Resolvyn is and why its answers can be trusted: judgment, tools, memory, a truth gate, and people in the loop.",
};

const TOC = [
  ["idea", "The idea"],
  ["journey", "One turn, step by step"],
  ["jev", "Jev, the judgment layer"],
  ["router", "The swarm router"],
  ["memory", "Memory"],
  ["truth", "The truth gate"],
  ["humans", "People in the loop"],
  ["learning", "Learning from first-time problems"],
  ["channels", "One brain, three channels"],
  ["architecture", "The architecture"],
  ["local", "Private and local"],
] as const;

/* ── layout helpers ──────────────────────────────────────────────────────────────────────────────────────────────── */

function Section({ id, kicker, title, lead, children }: { id: string; kicker: string; title: string; lead: string; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-24 space-y-6">
      <div className="max-w-2xl">
        <p className="text-sm font-medium text-success">{kicker}</p>
        <h2 className="mt-2 font-display text-3xl font-normal tracking-tight sm:text-4xl">{title}</h2>
        <p className="mt-3 leading-relaxed text-muted-foreground">{lead}</p>
      </div>
      {children}
    </section>
  );
}

const box = "rounded-xl border bg-card px-4 py-3 text-sm";

function Arrow({ className }: { className?: string }) {
  return <ArrowRight className={cn("hidden h-4 w-4 shrink-0 text-muted-foreground sm:block", className)} aria-hidden />;
}

function Node({ label, sub, tone = "plain" }: { label: string; sub?: string; tone?: "plain" | "brand" | "muted" | "warn" }) {
  return (
    <div
      className={cn(
        "min-w-[110px] flex-1 rounded-xl border px-3.5 py-3 text-center",
        tone === "brand" && "border-brand/50 bg-brand/10",
        tone === "muted" && "border-dashed bg-muted/40 text-muted-foreground",
        tone === "warn" && "border-warning/50 bg-warning/10",
        tone === "plain" && "bg-card",
      )}
    >
      <p className="text-sm font-medium text-foreground">{label}</p>
      {sub ? <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p> : null}
    </div>
  );
}

function Tag({ kind }: { kind: "rules" | "model" | "tools" | "people" }) {
  const t = {
    rules: "border-brand/40 bg-brand/10 text-success",
    model: "border-info/40 bg-info/10 text-info",
    tools: "border-warning/40 bg-warning/10 text-warning",
    people: "border-border bg-muted text-muted-foreground",
  }[kind];
  return <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider", t)}>{kind}</span>;
}

/* ── page ────────────────────────────────────────────────────────────────────────────────────────────────────────── */

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1240px] items-center justify-between px-6">
          <Link href="/" aria-label="Resolvyn home">
            <Logo size={30} />
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-muted-foreground sm:flex" aria-label="Site">
            <Link href="/" className="transition-colors hover:text-foreground">Home</Link>
            <Link href="/docs" className="font-medium text-foreground">How it works</Link>
            <Link href="/#benchmarks" className="transition-colors hover:text-foreground">Benchmarks</Link>
            <Link href="/ops" className="transition-colors hover:text-foreground">Team console</Link>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button asChild size="sm" className="rounded-full">
              <Link href="/talk">Talk to Riya</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* hero, with the brand's human in the corner */}
      <div className="grain relative isolate overflow-hidden border-b">
        <Aura strength={0.6} />
        <div className="relative mx-auto max-w-[1240px] px-6 pb-14 pt-14 sm:pt-20">
          <div className="max-w-2xl pr-24 sm:pr-0">
            <p className="text-sm font-medium text-success">How Resolvyn works</p>
            <h1 className="mt-3 font-display text-4xl font-normal leading-[1.05] tracking-tight sm:text-6xl">
              Support that only says what it has verified.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted-foreground">
              Most support bots let a language model decide and hope it stays honest. Resolvyn turns that around: rules decide, tools check, the model only finds the words, and a gate stops anything unverified from reaching the customer.
            </p>
          </div>
          <div className="pointer-events-none absolute -bottom-2 right-2 h-[170px] w-[130px] sm:right-8 sm:h-[300px] sm:w-[230px]" aria-hidden>
            <div className="absolute inset-x-4 bottom-0 h-3/4 rounded-full bg-brand/25 blur-3xl" />
            <Image
              src="/hero-human.png"
              alt=""
              fill
              sizes="230px"
              className="object-contain object-bottom opacity-95 [mask-image:linear-gradient(to_bottom,black_55%,transparent_100%)]"
            />
          </div>
        </div>
      </div>

      <div className="mx-auto grid max-w-[1240px] gap-12 px-6 py-14 lg:grid-cols-[200px_minmax(0,1fr)]">
        <aside className="hidden lg:block">
          <nav className="sticky top-24 space-y-1 text-sm" aria-label="On this page">
            <p className="pb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">On this page</p>
            {TOC.map(([id, label]) => (
              <a key={id} href={`#${id}`} className="block rounded-md px-2 py-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
                {label}
              </a>
            ))}
          </nav>
        </aside>

        <main className="min-w-0 space-y-20">
          {/* 1 ── the idea */}
          <Section id="idea" kicker="The idea" title="Decide with rules. Verify with tools. Let the model only phrase." lead="A language model is excellent at sounding right and unable to know whether it is. Resolvyn keeps the model out of every decision that matters and puts a check between it and the customer.">
            <div className="space-y-3">
              <div className="rounded-2xl border border-dashed bg-muted/30 p-4">
                <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">A typical AI agent</p>
                <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
                  <Node label="Caller" tone="muted" />
                  <Arrow />
                  <Node label="Language model" sub="decides and answers" tone="muted" />
                  <Arrow />
                  <Node label="“Your refund is done”" sub="said whether or not it is true" tone="muted" />
                </div>
              </div>
              <div className="rounded-2xl border border-brand/40 bg-brand/5 p-4">
                <p className="mb-3 text-xs font-medium uppercase tracking-wider text-success">Resolvyn</p>
                <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
                  <Node label="Caller" />
                  <Arrow />
                  <Node label="Jev" sub="rules read the request" tone="brand" />
                  <Arrow />
                  <Node label="Tools" sub="orders, payments, refunds" tone="brand" />
                  <Arrow />
                  <Node label="Model" sub="phrases verified facts" />
                  <Arrow />
                  <Node label="Truth gate" sub="drops the unverified" tone="brand" />
                  <Arrow />
                  <Node label="Caller hears it" />
                </div>
              </div>
            </div>
            <p className="max-w-2xl text-sm text-muted-foreground">
              So “your refund is processed” is only spoken after the refund service has returned a confirmed reference. Until then the customer hears the honest version: it is waiting for approval.
            </p>
          </Section>

          {/* 2 ── the journey */}
          <Section id="journey" kicker="One turn, step by step" title="What happens between a caller speaking and Riya answering" lead="Every turn runs the same eight steps. Look at the tags: the language model is involved in exactly one of them.">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {(
                [
                  [Ear, "Hear", "Speech becomes text. Order IDs, emails and names are pulled out.", "rules"],
                  [Sparkles, "Judge", "Jev scores intent, department, mood and urgency in about 13 ms.", "rules"],
                  [Brain, "Recall", "Policies, past cases and taught fixes come back from memory.", "rules"],
                  [ShieldCheck, "Decide", "Instant answer, real action, first-time problem, or a person.", "rules"],
                  [Wrench, "Act", "The right specialist runs real tools and reads the results.", "tools"],
                  [Hand, "Approve", "Risky steps such as refunds wait for a human to say yes.", "people"],
                  [MessageSquare, "Phrase", "The model turns verified facts into natural speech.", "model"],
                  [GraduationCap, "Gate and learn", "Unverified claims are dropped; the outcome is remembered.", "rules"],
                ] as [LucideIcon, string, string, "rules" | "model" | "tools" | "people"][]
              ).map(([Icon, title, text, tag], i) => (
                <div key={title} className="relative rounded-2xl border bg-card p-4">
                  <div className="flex items-center justify-between">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg border bg-background text-brand">
                      <Icon className="h-[18px] w-[18px]" />
                    </span>
                    <span className="font-display text-sm text-muted-foreground">0{i + 1}</span>
                  </div>
                  <p className="mt-3 font-medium">{title}</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{text}</p>
                  <div className="mt-3">
                    <Tag kind={tag} />
                  </div>
                </div>
              ))}
            </div>
          </Section>

          {/* 3 ── Jev */}
          <Section id="jev" kicker="Jev" title="A judgment layer that never waits for a model" lead="Jev is deterministic. It reads every sentence the caller says in milliseconds, so Riya can react at once, even on modest hardware. When it is unsure it asks the small local model one narrow question and never blocks the call.">
            <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
              <div className="rounded-2xl border bg-card p-5">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">The caller says</p>
                <p className="mt-2 font-display text-xl leading-snug">“I was charged twice for my earbuds, order ORD-83921. Can someone fix this?”</p>
                <div className="mt-5 flex flex-wrap gap-2 text-xs">
                  {[
                    ["Intent", "Duplicate payment"],
                    ["Department", "Billing"],
                    ["Order", "ORD-83921"],
                    ["Mood", "Worried"],
                    ["Urgency", "Medium"],
                    ["Talking to", "Riya"],
                    ["Wants a person", "Not yet"],
                  ].map(([k, v]) => (
                    <span key={k} className="rounded-full border bg-background px-3 py-1.5">
                      <span className="text-muted-foreground">{k}: </span>
                      <span className="font-medium text-foreground">{v}</span>
                    </span>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  ["~13 ms", "to judge a sentence, before any model runs"],
                  ["Side talk", "knows when the caller is speaking to someone else and stays quiet"],
                  ["Hinglish", "Hindi, English and mixed speech in the same call"],
                  ["Honest doubt", "low confidence triggers one small model question, never a guess"],
                ].map(([big, small]) => (
                  <div key={big} className="rounded-2xl border bg-card p-4">
                    <p className="font-display text-xl">{big}</p>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{small}</p>
                  </div>
                ))}
              </div>
            </div>
          </Section>

          {/* 4 ── router */}
          <Section id="router" kicker="The swarm router" title="Five departments compete. One wins." lead="Deciding who should handle a ticket is a scored competition, not an if-else chain. Every department scores the same ticket independently; only the winner runs, and a narrow result pauses for a person instead of guessing.">
            <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
              <div className="space-y-3 rounded-2xl border bg-card p-5">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Example: “charged twice for my earbuds”</p>
                {[
                  ["Billing", 0.91, true],
                  ["Order", 0.42, false],
                  ["Account", 0.2, false],
                  ["Technical", 0.13, false],
                  ["Other", 0.08, false],
                ].map(([name, v, win]) => (
                  <div key={name as string} className="flex items-center gap-3 text-sm">
                    <span className={cn("w-20 shrink-0", win ? "font-medium text-foreground" : "text-muted-foreground")}>{name as string}</span>
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-border/70">
                      <div className={cn("h-full rounded-full", win ? "bg-brand" : "bg-muted-foreground/40")} style={{ width: `${(v as number) * 100}%` }} />
                    </div>
                    <span className="w-10 text-right tabular-nums text-muted-foreground">{(v as number).toFixed(2)}</span>
                  </div>
                ))}
                <p className="border-t pt-3 text-xs text-muted-foreground">Illustrative scores. The other four departments are suppressed and never run.</p>
              </div>
              <div className="rounded-2xl border bg-card p-5">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">How a score is made</p>
                <div className="mt-4 space-y-2.5">
                  {[
                    ["Intent match", 50],
                    ["Domain words", 20],
                    ["Availability", 15],
                    ["Learned from corrections", 15],
                  ].map(([k, w]) => (
                    <div key={k as string}>
                      <div className="mb-1 flex justify-between text-sm">
                        <span>{k as string}</span>
                        <span className="tabular-nums text-muted-foreground">{w}%</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-border/70">
                        <div className="h-full rounded-full bg-brand" style={{ width: `${(w as number) * 2}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                <p className="mt-4 text-xs leading-relaxed text-muted-foreground">No model call and no training: scoring five departments costs about the same as scoring one.</p>
              </div>
            </div>
          </Section>

          {/* 5 ── memory */}
          <Section id="memory" kicker="Memory" title="Two memories: what the business knows, and what it has never seen" lead="Both are searched by meaning (a vector index) and by connection (a knowledge graph). They are kept apart on purpose, so a brand-new problem is never mistaken for a familiar one.">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border bg-card p-5">
                <p className="font-medium">Common memory</p>
                <p className="mt-1 text-sm text-muted-foreground">The rulebook: how this business does things.</p>
                <div className="mt-4 flex flex-wrap gap-2 text-xs">
                  {["Policies and SOPs", "Product and order data", "Every solved ticket", "Fixes a manager taught"].map((x) => (
                    <span key={x} className="rounded-full border bg-background px-3 py-1.5">{x}</span>
                  ))}
                </div>
                <p className="mt-4 text-xs text-success">Match found → instant answer or a real action.</p>
              </div>
              <div className="rounded-2xl border border-warning/40 bg-warning/5 p-5">
                <p className="font-medium">First-time-bug memory</p>
                <p className="mt-1 text-sm text-muted-foreground">Problems nothing in the rulebook explains.</p>
                <div className="mt-4 flex flex-wrap gap-2 text-xs">
                  {["Unknown error codes", "New device faults", "Open bugs being worked on"].map((x) => (
                    <span key={x} className="rounded-full border bg-background px-3 py-1.5">{x}</span>
                  ))}
                </div>
                <p className="mt-4 text-xs text-warning">No match → flagged to a person, never guessed.</p>
              </div>
            </div>
          </Section>

          {/* 6 ── truth gate */}
          <Section id="truth" kicker="The truth gate" title="Every sentence is checked before it is spoken" lead="After the model phrases its reply, the gate compares each sentence with the facts the tools verified. Anything carrying a date, amount, reference number, duration, completion claim or made-up social proof that is not in the evidence is removed.">
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border bg-card p-5">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">What the model drafted</p>
                <ul className="mt-3 space-y-2 text-sm">
                  {[
                    ["I can see the duplicate charge of ₹2,499 on your order.", true, "Verified by the payment tool"],
                    ["Your refund will arrive by Friday.", false, "Invented date"],
                    ["Other customers reported this issue too.", false, "Unverified claim"],
                    ["I have asked a manager to approve the refund.", true, "Verified: approval requested"],
                  ].map(([s, ok, why]) => (
                    <li key={s as string} className={cn("flex items-start justify-between gap-3 rounded-lg border px-3 py-2", ok ? "border-success/30 bg-success/5" : "border-danger/30 bg-danger/5")}>
                      <span className={cn(!ok && "text-muted-foreground line-through decoration-danger/60")}>{s as string}</span>
                      <span className={cn("shrink-0 text-[11px] font-medium", ok ? "text-success" : "text-danger")}>{why as string}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl border border-brand/40 bg-brand/5 p-5">
                <p className="text-xs font-medium uppercase tracking-wider text-success">What the customer hears</p>
                <p className="mt-3 font-display text-xl leading-snug">
                  “I can see the duplicate charge of ₹2,499 on your order. I have asked a manager to approve the refund.”
                </p>
                <p className="mt-5 text-sm text-muted-foreground">
                  In our trap test, 55 conversations built to make the model invent dates, prices and promises, every reply that reached the customer stayed truthful.{" "}
                  <Link href="/#benchmarks" className="font-medium text-foreground underline underline-offset-2">See the numbers</Link>.
                </p>
              </div>
            </div>
          </Section>

          {/* 7 ── humans */}
          <Section id="humans" kicker="People in the loop" title="Five ways a person steps in, none of them a dead end" lead="Any risky or uncertain step pauses the ticket and waits, even across a restart. A person resumes it with the action that fits, and the ticket carries on exactly where it stopped.">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {[
                ["Guide", "Point Riya in a direction: “check the courier first”."],
                ["Approve", "Say yes to a refund or other risky action."],
                ["Correct", "Fix a wrong routing or answer. It becomes a learning signal."],
                ["Override", "Take the decision yourself."],
                ["Teach", "Give a fix for a problem it has never seen."],
              ].map(([t, d]) => (
                <div key={t} className="rounded-2xl border bg-card p-4">
                  <p className="font-display text-lg">{t}</p>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{d}</p>
                </div>
              ))}
            </div>
            <p className="max-w-2xl text-sm text-muted-foreground">A refund above the set limit never runs before an explicit Approve. A resume on a ticket that is not paused is rejected, so a stray click can never issue a second refund.</p>
          </Section>

          {/* 8 ── learning */}
          <Section id="learning" kicker="Learning" title="A new problem is taught once and answered forever" lead="When Riya meets something no memory explains, she says so and asks for help instead of guessing. The fix she is taught helps that caller immediately and every caller after.">
            <div className="rounded-2xl border bg-card p-5">
              <ol className="grid gap-3 sm:grid-cols-4">
                {[
                  ["1", "Never seen it", "An unknown error code appears. Riya flags it to a manager."],
                  ["2", "A person teaches", "The manager types one suggestion."],
                  ["3", "Relayed live", "Riya passes it to the caller on the same call."],
                  ["4", "Remembered", "The next caller with the same fault is answered from memory."],
                ].map(([n, t, d]) => (
                  <li key={n} className="relative rounded-xl border bg-background p-4">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand text-sm font-medium text-brand-foreground">{n}</span>
                    <p className="mt-3 font-medium">{t}</p>
                    <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{d}</p>
                  </li>
                ))}
              </ol>
              <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
                <span className="h-px flex-1 bg-border" />
                the loop closes: step 4 becomes the rulebook step 1 reads next time
                <span className="h-px flex-1 bg-border" />
              </div>
            </div>
          </Section>

          {/* 9 ── channels */}
          <Section id="channels" kicker="One brain" title="Voice, chat and email share one memory" lead="Switch channel mid-issue and nothing is repeated. Every call or chat ends with a short summary email built from verified records only, and replies to that email land on the same ticket.">
            <div className="grid gap-3 sm:grid-cols-3">
              {(
                [
                  [Phone, "Voice", "Interruptible, streamed sentence by sentence, an acknowledgement before any model has started."],
                  [Headphones, "Chat", "The same brain in text, with a live ticket view beside it."],
                  [Mail, "Email", "Threads stay on one ticket. Loop guards stop auto-reply storms."],
                ] as [LucideIcon, string, string][]
              ).map(([Icon, t, d]) => (
                <div key={t} className="rounded-2xl border bg-card p-5">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl border bg-background text-brand">
                    <Icon className="h-5 w-5" />
                  </span>
                  <p className="mt-3 font-medium">{t}</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{d}</p>
                </div>
              ))}
            </div>
            <div className="flex items-center justify-center gap-3 rounded-xl border border-brand/40 bg-brand/5 px-4 py-3 text-sm">
              <LogoMark size={22} />
              <span className="font-medium">One orchestrator · one memory · one set of tools</span>
            </div>
          </Section>

          {/* 10 ── architecture */}
          <Section id="architecture" kicker="The architecture" title="The whole system on one page" lead="The original design sketch: the channels, the department agents, the two memories, Jev's query, the human gate and the first-time-bug loop shown in red.">
            <div className="overflow-hidden rounded-2xl border bg-card">
              <a href="/architecture-light.png" target="_blank" rel="noreferrer" className="block dark:hidden" aria-label="Open the architecture diagram full size">
                <Image src="/architecture-light.png" alt="Resolvyn architecture diagram" width={2000} height={1729} sizes="(min-width: 1024px) 1000px, 100vw" className="h-auto w-full" />
              </a>
              <a href="/architecture-dark.png" target="_blank" rel="noreferrer" className="hidden dark:block" aria-label="Open the architecture diagram full size">
                <Image src="/architecture-dark.png" alt="Resolvyn architecture diagram" width={2000} height={1729} sizes="(min-width: 1024px) 1000px, 100vw" className="h-auto w-full" />
              </a>
            </div>
            <p className="text-xs text-muted-foreground">Click the diagram to open it full size.</p>
          </Section>

          {/* 11 ── local */}
          <Section id="local" kicker="Private and local" title="It runs on a laptop, and your data stays there" lead="The live conversation uses a 4-billion-parameter model entirely on a 4 GB GPU. A larger model works on CPU after the call, only when the line is quiet. Nothing leaves the machine unless you choose to plug in a cloud model.">
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                ["4 GB", "of GPU memory is enough for the live model"],
                ["$0", "per minute for the language model"],
                ["On-device", "customer data stays on the machine by default"],
              ].map(([big, small]) => (
                <div key={big} className="rounded-2xl border bg-card p-5">
                  <p className="font-display text-3xl tracking-tight">{big}</p>
                  <p className="mt-1.5 text-sm text-muted-foreground">{small}</p>
                </div>
              ))}
            </div>
          </Section>

          <div className="flex flex-col items-center gap-4 rounded-2xl border bg-card px-6 py-12 text-center">
            <h2 className="font-display text-3xl tracking-tight sm:text-4xl">See it in action.</h2>
            <p className="max-w-md text-muted-foreground">Talk to Riya, or watch the same conversation from the team console.</p>
            <div className="flex flex-wrap justify-center gap-3">
              <Button asChild size="lg" className="rounded-full px-7">
                <Link href="/talk">Talk to Riya</Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="rounded-full px-7">
                <Link href="/ops">Open the team console</Link>
              </Button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
