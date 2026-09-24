import { EVENT_TYPE_LABEL } from "@/lib/constants";

interface HumanActionRecord {
  human_event_id: number;
  event_type: string;
  previous_ai_action: string | null;
  human_action: string;
  reason: string | null;
  timestamp: string;
}

/** spec §11, §23: this ticket's own human-intelligence history. */
export function TicketHumanActions({ actions }: { actions: HumanActionRecord[] }) {
  if (actions.length === 0) {
    return <p className="text-xs text-text-muted">No human intervention on this ticket yet.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {actions.map((a) => (
        <div key={a.human_event_id} className="text-xs">
          <p className="font-medium text-text-primary">
            {EVENT_TYPE_LABEL[a.event_type] ?? a.event_type}
          </p>
          {a.previous_ai_action && <p className="text-text-muted">AI: {a.previous_ai_action}</p>}
          <p className="text-text-body">{a.human_action}</p>
          {a.reason && <p className="text-text-muted">Reason: {a.reason}</p>}
        </div>
      ))}
    </div>
  );
}
