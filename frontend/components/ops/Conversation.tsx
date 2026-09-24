"use client";

import { useEffect, useRef } from "react";

import type { Message } from "@/features/types";
import { fmtClock } from "@/lib/format";
import { cx } from "@/lib/utils";

const WHO: Record<Message["sender"], string> = {
  CUSTOMER: "Caller",
  Resolvyn: "Resolvyn",
  HUMAN: "Team member",
  SYSTEM: "System",
};

/** project.md §16: the conversation reads like a real support conversation. Side-talk is shown
 *  dimmed and labelled so a human can see the AI correctly ignored it (docs/architecture.md §2.1). */
export function Conversation({ messages, live }: { messages: Message[]; live: boolean }) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [messages.length]);

  if (!messages.length) return <p className="text-sm text-text-muted">No messages yet.</p>;
  return (
    <div className="max-h-[420px] space-y-3 overflow-y-auto pr-1" aria-live={live ? "polite" : "off"}>
      {messages.map((m) => {
        const side = m.kind === "side_talk";
        const mine = m.sender === "CUSTOMER";
        return (
          <div key={m.message_id} className={cx("animate-fade-in flex flex-col", mine ? "items-start" : "items-end")}>
            <div className="mb-0.5 flex items-center gap-2 text-[11px] text-text-secondary">
              <span className="font-medium text-text-muted">{WHO[m.sender]}</span>
              <time dateTime={m.timestamp}>{fmtClock(m.timestamp)}</time>
              {side && <span className="rounded border border-border px-1 text-[10px] uppercase tracking-wide">talking to someone else</span>}
            </div>
            <p
              className={cx(
                "max-w-[85%] whitespace-pre-wrap rounded-lg border px-3 py-2 text-[13px] leading-relaxed",
                side
                  ? "border-dashed border-border bg-transparent italic text-text-secondary"
                  : mine
                    ? "border-border bg-card-elevated text-text-primary"
                    : m.sender === "HUMAN"
                      ? "border-info/40 bg-info/10 text-text-primary"
                      : "border-border bg-bg-secondary text-text-body",
              )}
            >
              {m.content}
            </p>
          </div>
        );
      })}
      <div ref={end} />
    </div>
  );
}
