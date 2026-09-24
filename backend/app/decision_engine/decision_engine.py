"""Decision Engine — docs/architecture.md §1, layer 4; §2.5 (solvable
rulebook consultation).

Analyze -> Plan -> Evaluate -> Choose Action, gated by decision criteria:
policy compliance, customer value, risk/fraud detection, confidence
threshold, human availability (all from the reference architecture).

Choose Action must resolve to exactly one of: AUTONOMOUS, CLARIFY, HUMAN.
A HUMAN outcome is what puts a ticket into WAITING_FOR_HUMAN
(docs/context.md, ticket status model) and is what human_intelligence/
acts on.

Not yet implemented: depends on judgment_service.judge() and
memory/rulebook.py both being wired up first.
"""

from typing import Literal, TypedDict

ActionChoice = Literal["AUTONOMOUS", "CLARIFY", "HUMAN"]


class Decision(TypedDict):
    action: ActionChoice
    reason: str


def choose_action(confidence: int, risk: str) -> Decision:
    raise NotImplementedError(
        "Wire up to judgment_service + memory/rulebook.py "
        "(see docs/architecture.md §1, Decision Engine)."
    )
