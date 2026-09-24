"use client";

import { useEffect, useRef, useState } from "react";

import { Button, inputCls } from "@/components/ui/primitives";
import type { CustomerProfile } from "@/features/types";
import type { AgentStatus, CallStatus, Line } from "@/lib/useCall";
import { cx } from "@/lib/utils";

const STATUS_TEXT: Record<AgentStatus, string> = { listening: "Riya is listening", thinking: "Riya is thinking…", speaking: "Riya is speaking" };

function VoiceBars({ active }: { active: boolean }) {
  return (
    <div className="flex h-7 items-center gap-[3px]" aria-hidden>
      {[0, 1, 2, 3, 4].map((i) => (
        <span key={i} className={cx("w-[3px] rounded bg-text-max", active ? "voice-bar h-full" : "h-1 opacity-40")} style={{ animationDelay: `${i * 110}ms` }} />
      ))}
    </div>
  );
}

/** Start / run a call or chat with the agent (docs/architecture.md: Call, Text, Email, Audio channels). */
export function CallPanel(props: {
  customers: CustomerProfile[];
  status: CallStatus;
  agentStatus: AgentStatus;
  lines: Line[];
  interim: string;
  error: string | null;
  muted: boolean;
  sttSupported: boolean;
  ttsFallback: boolean;
  sttMode: "server" | "browser" | "none";
  customerId: string;
  onCustomer: (id: string) => void;
  onStart: (o: { customerId?: string; mode: "voice" | "chat"; lang: "en" | "hi" }) => void;
  onSend: (t: string) => void;
  onEnd: () => void;
  onMute: () => void;
  onReset: () => void;
  agentName: string;
}) {
  const { status, agentStatus, lines, interim, error, muted, sttSupported, ttsFallback, sttMode, customerId, customers } = props;
  const [mode, setMode] = useState<"voice" | "chat">("voice");
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [text, setText] = useState("");
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [lines.length, interim]);
  useEffect(() => {
    if (!sttSupported) setMode("chat");
  }, [sttSupported]);

  const live = status === "live" || status === "connecting";

  return (
    <section className="rounded-lg border border-border bg-card" aria-label="Talk to support">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-text-max text-sm font-semibold text-black" aria-hidden>
            {props.agentName[0]}
          </div>
          <div>
            <p className="text-sm font-semibold text-text-primary">{props.agentName}</p>
            <p className="text-xs text-text-muted">Nova Retail support</p>
          </div>
        </div>
        {live && (
          <div className="flex items-center gap-3" role="status" aria-live="polite">
            <VoiceBars active={agentStatus === "speaking"} />
            <span className="text-xs text-text-body">{status === "connecting" ? "Connecting…" : STATUS_TEXT[agentStatus]}</span>
          </div>
        )}
      </header>

      {!live && status !== "ended" && (
        <div className="space-y-4 p-4">
          <div>
            <label htmlFor="who" className="mb-1 block text-[11px] uppercase tracking-wide text-text-muted">
              You are calling as
            </label>
            <select id="who" className={inputCls} value={customerId} onChange={(e) => props.onCustomer(e.target.value)}>
              <option value="">Guest (Riya will ask who you are)</option>
              {customers.map((c) => (
                <option key={c.customer_id} value={c.customer_id}>
                  {c.name} · {c.plan}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="mb-1 text-[11px] uppercase tracking-wide text-text-muted">Channel</p>
              <div className="grid grid-cols-2 gap-1 rounded border border-border p-1" role="radiogroup" aria-label="Channel">
                {(["voice", "chat"] as const).map((m) => (
                  <button key={m} role="radio" aria-checked={mode === m} disabled={m === "voice" && !sttSupported} onClick={() => setMode(m)} className={cx("rounded py-1 text-xs font-medium disabled:opacity-40", mode === m ? "bg-text-max text-black" : "text-text-muted hover:text-text-primary")}>
                    {m === "voice" ? "Voice call" : "Chat"}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-1 text-[11px] uppercase tracking-wide text-text-muted">Language</p>
              <div className="grid grid-cols-2 gap-1 rounded border border-border p-1" role="radiogroup" aria-label="Language">
                {(["en", "hi"] as const).map((l) => (
                  <button key={l} role="radio" aria-checked={lang === l} onClick={() => setLang(l)} className={cx("rounded py-1 text-xs font-medium", lang === l ? "bg-text-max text-black" : "text-text-muted hover:text-text-primary")}>
                    {l === "en" ? "English" : "हिन्दी"}
                  </button>
                ))}
              </div>
            </div>
          </div>
          {!sttSupported && <p className="text-xs text-warning">Voice calls need Chrome or Edge. Chat works in any browser.</p>}
          {error && <p role="alert" className="text-xs text-danger">{error}</p>}
          <Button variant="primary" className="w-full py-3 text-base" onClick={() => props.onStart({ customerId: customerId || undefined, mode, lang })}>
            {mode === "voice" ? "Call Riya" : "Start chat"}
          </Button>
          <p className="text-center text-[11px] text-text-secondary">Use headphones for the best voice experience. Speak naturally — you can interrupt at any time.</p>
        </div>
      )}

      {(live || status === "ended") && (
        <div className="flex h-[520px] flex-col">
          <div className="flex-1 space-y-2.5 overflow-y-auto px-4 py-3" aria-live="polite">
            {lines.map((l) => (
              <div key={l.id} className={cx("animate-fade-in flex", l.who === "you" || l.who === "side" ? "justify-end" : "justify-start")}>
                <p
                  className={cx(
                    "max-w-[85%] rounded-lg border px-3 py-2 text-[13px] leading-relaxed",
                    l.who === "you" && "border-border bg-card-elevated text-text-primary",
                    l.who === "agent" && "border-border bg-bg-secondary text-text-body",
                    l.who === "human" && "border-info/40 bg-info/10 text-text-primary",
                    l.who === "side" && "border-dashed border-border bg-transparent italic text-text-secondary",
                  )}
                >
                  {l.who === "human" && <span className="mb-0.5 block text-[10px] uppercase tracking-wide text-info">Team member</span>}
                  {l.who === "side" && <span className="mb-0.5 block text-[10px] uppercase not-italic tracking-wide">Talking to someone else · Riya stays quiet</span>}
                  {l.text}
                </p>
              </div>
            ))}
            {interim && (
              <div className="flex justify-end">
                <p className="max-w-[85%] rounded-lg border border-dashed border-border px-3 py-2 text-[13px] italic text-text-muted">{interim}…</p>
              </div>
            )}
            <div ref={end} />
          </div>

          {status === "ended" ? (
            <div className="border-t border-border p-4">
              <p className="mb-2 text-sm text-text-body">The call has ended. Your ticket stays open on the right and updates in real time.</p>
              <Button variant="primary" onClick={props.onReset}>
                New call
              </Button>
            </div>
          ) : (
            <div className="border-t border-border p-3">
              {error && <p role="alert" className="mb-2 text-xs text-danger">{error}</p>}
              {ttsFallback && <p className="mb-2 text-[11px] text-text-muted">Using your browser&apos;s voice (the neural voice service is unreachable).</p>}
              {sttMode !== "none" && (
                <p className="mb-2 text-[11px] text-text-secondary">
                  Speech recognition: {sttMode === "server" ? "Gnani real-time (streamed from your microphone)" : "your browser"}
                </p>
              )}
              <form
                className="flex items-center gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  props.onSend(text);
                  setText("");
                }}
              >
                <input className={inputCls} placeholder={mode === "voice" ? "Or type here…" : "Type your message…"} value={text} onChange={(e) => setText(e.target.value)} aria-label="Message" />
                <Button type="submit" disabled={!text.trim()}>
                  Send
                </Button>
                {mode === "voice" && (
                  <Button type="button" onClick={props.onMute} aria-pressed={muted} title={muted ? "Unmute microphone" : "Mute microphone"}>
                    {muted ? "Unmute" : "Mute"}
                  </Button>
                )}
                <Button type="button" variant="danger" onClick={props.onEnd}>
                  End
                </Button>
              </form>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
