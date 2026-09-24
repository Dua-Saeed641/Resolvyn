/** Mirrors backend/app/models/learning_signal.py. */
export interface LearningSignal {
  signal_id: number;
  ticket_id: string;
  source_event?: string | null;
  signal_type: string;
  expected_action?: string | null;
  observed_action?: string | null;
  description?: string | null;
  timestamp: string;
}
