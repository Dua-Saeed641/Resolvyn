/**
 * Single source of truth for app-wide vocabulary (docs/project.md §33-36).
 * Every status/priority/confidence label in the UI must come from here —
 * do not inline these strings or invent new states elsewhere (docs/claude.md).
 */

export const TICKET_STATUSES = [
  "NEW",
  "ANALYZING",
  "ROUTING",
  "ACTIVE",
  "WAITING_FOR_HUMAN",
  "VERIFYING",
  "RESOLVED",
  "FAILED",
] as const;
export type TicketStatus = (typeof TICKET_STATUSES)[number];

export const AGENT_STATES = [
  "IDLE",
  "ANALYZING",
  "RETRIEVING",
  "ACTING",
  "VERIFYING",
  "WAITING",
  "COMPLETED",
  "ERROR",
] as const;
export type AgentState = (typeof AGENT_STATES)[number];

export const PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
export type Priority = (typeof PRIORITIES)[number];

export const SENTIMENTS = ["Positive", "Neutral", "Frustrated", "Angry"] as const;
export type Sentiment = (typeof SENTIMENTS)[number];

export const HUMAN_ACTIONS = ["GUIDE", "APPROVE", "CORRECT", "OVERRIDE", "TEACH"] as const;
export type HumanActionType = (typeof HUMAN_ACTIONS)[number];

/** project.md §35: prototype UI thresholds, not model-calibration claims. */
export function confidenceLabel(confidence: number): "High" | "Medium" | "Low" {
  if (confidence >= 90) return "High";
  if (confidence >= 75) return "Medium";
  return "Low";
}

/** Status → accent color, per project.md §7 (color communicates meaning, used sparingly). */
export const STATUS_COLOR: Record<TicketStatus, "success" | "warning" | "danger" | "info" | "muted"> = {
  NEW: "info",
  ANALYZING: "muted",
  ROUTING: "muted",
  ACTIVE: "info",
  WAITING_FOR_HUMAN: "warning",
  VERIFYING: "muted",
  RESOLVED: "success",
  FAILED: "danger",
};
