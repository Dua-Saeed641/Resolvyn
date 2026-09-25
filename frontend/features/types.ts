/** Mirrors backend serialisers (backend/app/services/ticket_service.py). */

import type { AgentState, Department, TicketStatus } from "@/lib/constants";

export interface KnowledgeRef {
  chunk_id: number;
  title: string;
  kind: string;
  store: string;
  department: string;
  score: number;
  via: string;
  ref_ticket_id?: string | null;
}

export interface Ticket {
  ticket_id: string;
  customer_id: string | null;
  customer_name: string | null;
  subject: string;
  status: TicketStatus;
  intent: string | null;
  sentiment: string | null;
  urgency: string | null;
  priority: string;
  assigned_agent: Department | null;
  confidence: number | null;
  confidence_label: string;
  order_id: string | null;
  channel: string;
  language: string;
  session_id: string | null;
  call_active: boolean;
  resolution_path: string | null;
  handled_by: "AI" | "HUMAN";
  escalated: boolean;
  escalation_reason: string | null;
  is_first_time_bug: boolean;
  needs_human: boolean;
  one_line_summary: string | null;
  detailed_summary?: string | null;
  deep_summary?: string | null;
  next_step: string | null;
  context_doc?: string | null;
  jira_key: string | null;
  jira_status: string | null;
  assignee: string | null;
  knowledge: KnowledgeRef[];
  guidance: string[];
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  resolution_time: number | null;
}

export interface Message {
  message_id: number;
  ticket_id: string;
  sender: "CUSTOMER" | "Resolvyn" | "HUMAN" | "SYSTEM";
  content: string;
  kind: "speech" | "chat" | "side_talk" | "system";
  timestamp: string;
}

export interface AgentEvent {
  event_id: number;
  ticket_id: string;
  agent: string;
  event_type: string;
  description: string;
  status: string | null;
  meta: Record<string, unknown>;
  timestamp: string;
}

export interface ToolCall {
  tool_call_id: number;
  ticket_id: string;
  tool_name: string;
  status: "NOT_STARTED" | "WAITING" | "COMPLETED" | "FAILED";
  request: Record<string, unknown>;
  response: unknown;
  timestamp: string;
}

export interface PendingAction {
  action_id: number;
  ticket_id: string;
  action_type: string;
  summary: string;
  params: { order_id?: string; transaction_id?: string; amount?: number; reason?: string };
  risk: string;
  policy: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "EXECUTED" | "FAILED";
  result: unknown;
  decided_by: string | null;
  created_at: string;
  decided_at: string | null;
}

export interface HumanAction {
  human_event_id: number;
  ticket_id: string | null;
  event_type: string;
  previous_ai_action: string | null;
  human_action: string;
  reason: string | null;
  operator: string;
  timestamp: string;
}

export interface FirstTimeBug {
  bug_id: number;
  ticket_id: string;
  title: string;
  detail: string;
  department: string;
  status: "OPEN" | "SUGGESTED";
  suggestion: string | null;
  suggested_by: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface TicketDetail extends Ticket {
  messages: Message[];
  events: AgentEvent[];
  tool_calls: ToolCall[];
  pending_actions: PendingAction[];
  human_actions: HumanAction[];
  bugs: FirstTimeBug[];
}

export interface AgentInfo {
  name: Department;
  status: AgentState;
  current_ticket_id: string | null;
  current_operation: string | null;
  resolved_today: number;
  current_tickets?: number;
  avg_confidence?: number | null;
}

export interface Stats {
  tickets_total: number;
  active: number;
  resolved: number;
  handled_by_ai: number;
  escalated: number;
  waiting_for_human: number;
  human_touched: number;
  first_time_bugs: number;
  open_bugs: number;
  pending_approvals: number;
  live_calls: number;
  avg_resolution_seconds: number | null;
  avg_confidence: number | null;
  human_interventions: number;
  human_by_type: Record<string, number>;
  learning_signals: number;
  intents: Record<string, number>;
  agent_activity: Record<string, number>;
  paths: Record<string, number>;
  sentiment: Record<string, number>;
  volume_by_hour: { label: string; count: number }[];
  ai_resolution_rate: number | null;
}

export interface LearningSignal {
  signal_id: number;
  code: string;
  ticket_id: string;
  source_event: string | null;
  signal_type: string;
  expected_action: string | null;
  observed_action: string | null;
  description: string | null;
  timestamp: string;
}

export interface CustomerProfile {
  customer_id: string;
  name: string;
  email: string | null;
  phone_last4: string | null;
  plan: string;
  account_age_years: number;
  recent_sentiment: string;
  open_issues: number;
  previous_tickets: number;
  ticket_count?: number;
  resolved?: number;
  open?: number;
  last_contact?: string | null;
}

export interface CustomerTicketView {
  ticket_id: string;
  subject: string;
  status: TicketStatus;
  status_label: string;
  department: string | null;
  customer_name: string | null;
  priority: string;
  escalated: boolean;
  needs_human: boolean;
  call_active: boolean;
  created_at: string;
  updated_at: string;
  timeline: { time: string; text: string }[];
  actions: { type: string; summary: string; status: string; result: unknown }[];
}

export interface LlmStatus {
  prefer: string;
  live_ready: boolean;
  deep_ready: boolean;
  latency_ms: Record<string, number>;
  engine: {
    ready: boolean;
    loading: boolean;
    error: string | null;
    tiers?: Record<string, { file_present: boolean; model: string; description: string }>;
    deep_alive?: boolean;
    main_alive?: boolean;
  };
  cloud: { configured: boolean; model: string | null; error: string | null };
}

export interface SystemInfo {
  product: string;
  business: string;
  agent: string;
  llm: LlmStatus;
  tts: { engine: string; providers?: string[]; voice?: string; voice_en: string; voice_hi: string; cached: number; error: string | null };
  stt?: { provider: string; gnani: boolean };
  live_calls: number;
  ops_clients: number;
}

export interface KnowledgeDoc {
  document_id: number;
  title: string;
  category: string;
  kind: string;
  department: string;
  chunk_count: number;
  referenced_in_tickets: number;
  source_name: string;
  last_updated: string;
}

export interface Rule {
  rule_id: number;
  topic: string;
  knowledge: string;
  source: string;
  ticket_id: string | null;
  created_at: string;
}

export type RulebookByDepartment = Record<string, { rules: Rule[]; sop_chunks: number; documents: string[] }>;

export interface GraphSnapshot {
  nodes: { id: string; type: string; label: string; weight: number; store: string }[];
  edges: { src: string; dst: string; relation: string; weight: number }[];
  stats: { nodes: number; edges: number };
}
