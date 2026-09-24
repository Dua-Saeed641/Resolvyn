"""Judgment & Intelligence Core — docs/architecture.md §1, layer 3 (Jev).

Scores an enriched message for intent, sentiment, urgency, and an overall
confidence/escalation signal. Confidence bands are fixed UI thresholds,
not model-calibration claims (project.md §35): High >=90, Medium 75-89,
Low <75.

Not yet implemented: requires either a real LLM call or a deterministic
mock classifier over docs/context.md's known intents (Duplicate Payment,
Refund Status, Account Access, Shipping Delay, Technical Issue).
"""

from typing import TypedDict


class Judgment(TypedDict):
    intent: str
    sentiment: str
    urgency: str
    confidence: int


def judge(enriched_text: str) -> Judgment:
    raise NotImplementedError(
        "Wire up to an LLM call or a deterministic mock classifier "
        "(see docs/architecture.md §1, Judgment & Intelligence Core)."
    )
