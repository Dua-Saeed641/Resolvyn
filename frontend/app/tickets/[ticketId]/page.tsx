import { notFound } from "next/navigation";

import { AIUnderstanding } from "@/components/tickets/AIUnderstanding";
import { ActionVerification } from "@/components/tools/ActionVerification";
import { ConversationPanel } from "@/components/tickets/ConversationPanel";
import { KnowledgePanel } from "@/components/tickets/KnowledgePanel";
import { AppShell } from "@/components/layout/AppShell";
import { PriorityBadge } from "@/components/ui/PriorityBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TicketActions } from "@/components/tickets/TicketActions";
import { TicketCustomerContext } from "@/components/tickets/TicketCustomerContext";
import { TicketHumanActions } from "@/components/human-intelligence/TicketHumanActions";
import { TicketStatusPipeline } from "@/components/tickets/TicketStatusPipeline";
import { TicketTimeline } from "@/components/tickets/TicketTimeline";
import { ToolCall as ToolCallItem } from "@/components/tools/ToolCall";
import type { Customer } from "@/features/customers/types";
import type { Message, Ticket, TicketEvent, TicketKnowledge, ToolCallRecord } from "@/features/tickets/types";
import { api, ApiError } from "@/lib/api";
import { timeAgo } from "@/lib/utils";

/** spec §9-19: the single most important page — makes the full ticket
 * operational state legible to a support operator in a few seconds. */
export default async function TicketDetailPage({ params }: { params: { ticketId: string } }) {
  const { ticketId } = params;

  let ticket: Ticket;
  try {
    ticket = await api.get<Ticket>(`/tickets/${ticketId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const [messages, timeline, toolCalls, knowledge, customer, customerTickets, humanActions, routing] =
    await Promise.all([
      api.get<Message[]>(`/tickets/${ticketId}/messages`),
      api.get<TicketEvent[]>(`/tickets/${ticketId}/timeline`),
      api.get<ToolCallRecord[]>(`/tickets/${ticketId}/tool-calls`),
      api.get<TicketKnowledge>(`/tickets/${ticketId}/knowledge`),
      api.get<Customer>(`/customers/${ticket.customer_id}`),
      api.get<Ticket[]>(`/customers/${ticket.customer_id}/tickets`),
      api.get<{ human_event_id: number; event_type: string; previous_ai_action: string | null; human_action: string; reason: string | null; timestamp: string }[]>(
        `/human-intelligence?tab=interventions&ticket_id=${ticketId}`
      ),
      api.get<{ ticket_id: string; reason: string }[]>("/routing"),
    ]);

  const routingReason = routing.find((r) => r.ticket_id === ticketId)?.reason ?? null;
  const pendingToolCall = toolCalls.find((t) => t.status === "WAITING") ?? null;

  const canApprove = ticket.status === "WAITING_FOR_HUMAN" && pendingToolCall !== null;
  const canGuide = ticket.status === "WAITING_FOR_HUMAN" && pendingToolCall === null;
  const canCorrectOrOverride = ticket.status !== "RESOLVED" && ticket.status !== "FAILED";

  return (
    <AppShell title={ticket.ticket_id}>
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col gap-3 rounded border border-border bg-card p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <p className="text-base font-semibold text-text-primary">{ticket.ticket_id}</p>
                <StatusBadge status={ticket.status} />
                <PriorityBadge priority={ticket.priority} />
              </div>
              <p className="mt-1 text-sm text-text-body">{ticket.subject}</p>
              <p className="mt-1 text-xs text-text-muted">
                {customer.name} · {ticket.assigned_agent ?? "Unassigned"} · Updated {timeAgo(ticket.updated_at)}
              </p>
            </div>
            <TicketActions
              ticketId={ticket.ticket_id}
              intent={ticket.intent}
              pendingAction={pendingToolCall?.tool_name ?? null}
              confidence={ticket.confidence}
              canGuide={canGuide}
              canApprove={canApprove}
              canCorrectOrOverride={canCorrectOrOverride}
              isFirstTimeBug={knowledge.is_first_time_bug}
            />
          </div>
          <TicketStatusPipeline status={ticket.status} />
        </div>

        {/* Conversation | AI Operations | Customer Context */}
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded border border-border bg-card p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Customer conversation</p>
            <div className="mt-3">
              <ConversationPanel messages={messages} />
            </div>
          </div>
          <div className="rounded border border-border bg-card p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">AI operations</p>
            <div className="mt-3">
              <AIUnderstanding ticket={ticket} routingReason={routingReason} />
            </div>
          </div>
          <div className="rounded border border-border bg-card p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Customer context</p>
            <div className="mt-3">
              <TicketCustomerContext customer={customer} relatedTickets={customerTickets} currentTicket={ticket} />
            </div>
          </div>
        </div>

        {/* Knowledge | Tools */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-text-muted">Knowledge / rulebook</p>
            <KnowledgePanel knowledge={knowledge} />
          </div>
          <div className="flex flex-col gap-3">
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-text-muted">Tool activity</p>
              <div className="rounded border border-border">
                {toolCalls.map((t) => (
                  <ToolCallItem key={t.tool_call_id} name={t.tool_name} status={t.status} />
                ))}
              </div>
            </div>
            <ActionVerification toolCalls={toolCalls} />
          </div>
        </div>

        {/* Human Intelligence | Timeline */}
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded border border-border bg-card p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Human intelligence</p>
            <div className="mt-3">
              <TicketHumanActions actions={humanActions} />
            </div>
          </div>
          <div className="rounded border border-border bg-card p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Timeline</p>
            <div className="mt-3">
              <TicketTimeline
                entries={timeline.map((e) => ({
                  timestamp: new Date(e.timestamp).toLocaleTimeString(undefined, { hour12: false }),
                  label: e.description ?? e.event_type,
                  detail: e.agent,
                }))}
              />
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
