"use client";

import { fmtClock } from "@/lib/format";
import type { AgentEvent } from "@/features/types";
import { cx } from "@/lib/utils";

const TONE: Record<string, string> = {
  FIRST_TIME_BUG_FLAGGED: "text-danger",
  ESCALATED: "text-warning",
  ACTION_PROPOSED: "text-warning",
  ACTION_APPROVED: "text-success",
  ACTION_VERIFIED: "text-success",
  TICKET_RESOLVED: "text-success",
  HUMAN_GUIDANCE: "text-info",
  HUMAN_TEACHING: "text-info",
  HUMAN_CORRECTION: "text-info",
  HUMAN_TAKEOVER: "text-info",
  ERROR: "text-danger",
  SLA_WARNING: "text-warning",
};

const LABEL: Record<string, string> = {
  TICKET_CREATED: "Ticket",
  INTENT_DETECTED: "Jev",
  AGENT_ASSIGNED: "Routing",
  MEMORY_RETRIEVED: "Memory",
  KNOWLEDGE_RETRIEVED: "Knowledge",
  DECISION: "Decision",
  TOOL_CALLED: "Tool",
  ACTION_PROPOSED: "Proposed",
  ACTION_APPROVED: "Approved",
  ACTION_REJECTED: "Rejected",
  ACTION_EXECUTED: "Executed",
  ACTION_VERIFIED: "Verified",
  RESPONSE_GENERATED: "Response",
  SIDE_TALK_DETECTED: "Side talk",
  FIRST_TIME_BUG_FLAGGED: "First-time bug",
  ESCALATED: "Escalated",
  CONTEXT_DOC_CREATED: "Context doc",
  JIRA_SYNCED: "Jira · simulated",
  SLA_WARNING: "SLA",
  HUMAN_GUIDANCE: "Guide",
  HUMAN_TEACHING: "Teach",
  HUMAN_CORRECTION: "Correct",
  HUMAN_TAKEOVER: "Override",
  TICKET_RESOLVED: "Resolved",
  CALL_ENDED: "Call",
  SUMMARY_UPDATED: "Summary",
  ERROR: "Error",
};

/** project.md §37: the activity timeline — one of the most important parts of the demo. */
export function Timeline({ events, showTicket = false, newestFirst = false }: { events: AgentEvent[]; showTicket?: boolean; newestFirst?: boolean }) {
  const list = newestFirst ? events : events;
  return (
    <ol className="relative space-y-0">
      {list.map((e) => (
        <li key={e.event_id} className="animate-fade-in grid grid-cols-[64px_92px_minmax(0,1fr)] items-baseline gap-3 border-b border-border/60 py-1.5 text-[13px] last:border-b-0">
          <time className="tabular-nums text-xs text-text-secondary" dateTime={e.timestamp}>
            {fmtClock(e.timestamp)}
          </time>
          <span className={cx("truncate text-xs font-medium", TONE[e.event_type] ?? "text-text-muted")}>{LABEL[e.event_type] ?? e.event_type}</span>
          <span className="min-w-0 text-text-body">
            {showTicket && <span className="mr-2 font-medium text-text-primary">{e.ticket_id}</span>}
            {e.description}
            {e.status === "FAILED" && <span className="ml-2 text-xs text-danger">✕ failed</span>}
          </span>
        </li>
      ))}
    </ol>
  );
}
