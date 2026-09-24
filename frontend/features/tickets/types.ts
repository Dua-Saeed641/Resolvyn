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
}

/** Mirrors backend/app/models/message.py. */
export interface Message {
  message_id: number;
  ticket_id: string;
  sender: "CUSTOMER" | "Resolvyn" | "HUMAN";
  content: string;
  timestamp: string;
}
