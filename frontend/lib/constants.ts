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

/**
 * backend/app/models/human_action.py stores the noun form of each action
 * (GUIDANCE/APPROVAL/CORRECTION/OVERRIDE/TEACHING, project.md §43) while
 * the UI buttons use the verb form (HUMAN_ACTIONS above, project.md §22).
 * This maps a recorded event's `event_type` back to the same verb label
 * shown on the button that created it.
 */
export const EVENT_TYPE_LABEL: Record<string, string> = {
  GUIDANCE: "Guide",
  APPROVAL: "Approve",
  CORRECTION: "Correct",
  OVERRIDE: "Override",
  TEACHING: "Teach",
};

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

/** spec §37: only HIGH/CRITICAL get strong visual emphasis. */
export const PRIORITY_COLOR: Record<Priority, "danger" | "warning" | "muted"> = {
  LOW: "muted",
  MEDIUM: "muted",
  HIGH: "warning",
  CRITICAL: "danger",
};

export const HUMAN_ACTION_LABELS: Record<HumanActionType, string> = {
  GUIDE: "Guide",
  APPROVE: "Approve",
  CORRECT: "Correct",
  OVERRIDE: "Override",
  TEACH: "Teach",
};
