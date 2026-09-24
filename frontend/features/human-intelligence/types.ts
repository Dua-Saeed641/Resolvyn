import type { HumanActionType } from "@/lib/constants";

/** Mirrors backend/app/models/human_action.py. */
export interface HumanAction {
  human_event_id: number;
  ticket_id: string;
  event_type: HumanActionType;
  previous_ai_action?: string | null;
  human_action: string;
  reason?: string | null;
  timestamp: string;
}
