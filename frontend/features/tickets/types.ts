import type { Priority, Sentiment, TicketStatus } from "@/lib/constants";

/** Mirrors backend/app/models/ticket.py — keep the two in sync. */
export interface Ticket {
  ticket_id: string;
  customer_id: string;
  subject: string;
  status: TicketStatus;
  intent: string | null;
  sentiment: Sentiment | null;
  urgency: "Low" | "Medium" | "High" | null;
  priority: Priority;
  assigned_agent: string | null;
  confidence: number | null;
  order_id?: string | null;
  created_at: string;
  updated_at: string;
  resolution_time: number | null;
}

/** Mirrors backend/app/models/message.py. */
export interface Message {
  message_id: number;
  ticket_id: string;
  sender: "CUSTOMER" | "Resolvyn" | "HUMAN";
  content: string;
  timestamp: string;
}

/** Mirrors backend/app/models/agent_event.py — drives the ticket timeline. */
export interface TicketEvent {
  event_id: number;
  ticket_id: string;
  agent: string;
  event_type: string;
  description: string | null;
  status: string | null;
  timestamp: string;
}

/** Mirrors backend/app/models/tool_call.py. */
export interface ToolCallRecord {
  tool_call_id: number;
  ticket_id: string;
  tool_name: string;
  status: "NOT_STARTED" | "WAITING" | "COMPLETED" | "FAILED";
  request: string | null;
  response: string | null;
  timestamp: string;
}

export interface KnowledgeMatch {
  title: string;
  category: string;
  similarity: number;
}

export interface TicketKnowledge {
  documents: KnowledgeMatch[];
  is_first_time_bug: boolean;
}
