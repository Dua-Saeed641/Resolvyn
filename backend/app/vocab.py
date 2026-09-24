"""Backend mirror of frontend/lib/constants.ts (docs/claude.md, "Vocabulary").

Keep in sync with the frontend file. These are the only values the API may use.
"""

TICKET_STATUSES = (
    "NEW", "ANALYZING", "ROUTING", "ACTIVE", "WAITING_FOR_HUMAN", "VERIFYING", "RESOLVED", "FAILED",
)
AGENT_STATES = (
    "IDLE", "ANALYZING", "RETRIEVING", "ACTING", "VERIFYING", "WAITING", "COMPLETED", "ERROR",
)
PRIORITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
SENTIMENTS = ("Positive", "Neutral", "Frustrated", "Angry")
HUMAN_ACTIONS = ("GUIDE", "APPROVE", "CORRECT", "OVERRIDE", "TEACH")

# Department agents chosen "on the basis of the user query" (docs/architecture.md §2.3).
DEPARTMENTS = ("Technical", "Billing", "Account", "Order", "Other")

# Human event types stored in HumanAction.event_type (project.md §43).
HUMAN_EVENT_FOR_ACTION = {
    "GUIDE": "GUIDANCE",
    "APPROVE": "APPROVAL",
    "CORRECT": "CORRECTION",
    "OVERRIDE": "OVERRIDE",
    "TEACH": "TEACHING",
}


def confidence_label(confidence: int | None) -> str:
    """project.md §35: UI thresholds only, not calibration claims."""
    if confidence is None:
        return "Low"
    if confidence >= 90:
        return "High"
    if confidence >= 75:
        return "Medium"
    return "Low"
