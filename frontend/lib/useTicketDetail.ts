"use client";

import { useCallback, useEffect, useState } from "react";

import type { TicketDetail } from "@/features/types";
import { api } from "@/lib/api";
import { useLive, type LiveEvent } from "@/lib/live";

/** Full ticket for the team side, kept live by the /ws/ops stream. */
export function useTicketDetail(ticketId: string) {
  const { subscribe } = useLive();
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setDetail(await api.get<TicketDetail>(`/tickets/${ticketId}`));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load ticket");
    }
  }, [ticketId]);

  useEffect(() => {
    setDetail(null);
    load();
    const t = setInterval(load, 20000); // safety net; live events do the real work
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    return subscribe((e: LiveEvent) => {
      const mine = e.ticket_id === ticketId || e.ticket?.ticket_id === ticketId || e.message?.ticket_id === ticketId ||
        e.event?.ticket_id === ticketId || e.tool_call?.ticket_id === ticketId || e.action?.ticket_id === ticketId ||
        e.bug?.ticket_id === ticketId;
      if (!mine) return;
      setDetail((d) => {
        if (!d) return d;
        switch (e.type) {
          case "ticket_update":
            return { ...d, ...e.ticket };
          case "summary":
            return {
              ...d,
              ...(e.one_line_summary !== undefined && { one_line_summary: e.one_line_summary }),
              ...(e.detailed_summary !== undefined && { detailed_summary: e.detailed_summary }),
              ...(e.deep_summary !== undefined && { deep_summary: e.deep_summary }),
              ...(e.next_step !== undefined && { next_step: e.next_step }),
            };
          case "message":
            return d.messages.some((m) => m.message_id === e.message.message_id) ? d : { ...d, messages: [...d.messages, e.message] };
          case "event":
            return d.events.some((x) => x.event_id === e.event.event_id) ? d : { ...d, events: [...d.events, e.event] };
          case "tool_call": {
            const i = d.tool_calls.findIndex((c) => c.tool_call_id === e.tool_call.tool_call_id);
            const next = [...d.tool_calls];
            if (i >= 0) next[i] = e.tool_call;
            else next.push(e.tool_call);
            return { ...d, tool_calls: next };
          }
          case "approval_request":
            return d.pending_actions.some((p) => p.action_id === e.action.action_id) ? d : { ...d, pending_actions: [...d.pending_actions, e.action] };
          case "approval_decided":
            return { ...d, pending_actions: d.pending_actions.map((p) => (p.action_id === e.action.action_id ? e.action : p)) };
          case "human_action":
            return d.human_actions.some((h) => h.human_event_id === e.action.human_event_id) ? d : { ...d, human_actions: [...d.human_actions, e.action] };
          case "bug_alert":
          case "bug_update": {
            const others = d.bugs.filter((b) => b.bug_id !== e.bug.bug_id);
            return { ...d, bugs: [...others, e.bug] };
          }
          default:
            return d;
        }
      });
    });
  }, [subscribe, ticketId]);

  return { detail, error, reload: load };
}
