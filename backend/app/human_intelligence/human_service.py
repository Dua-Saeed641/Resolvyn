"""Human Intelligence Layer — docs/context.md.

Exactly five actions, consistent across the whole app: Guide, Approve,
Correct, Override, Teach (project.md §22). Every action here must:
  1. write a HumanAction row (app/models/human_action.py),
  2. update ticket state where applicable (e.g. Approve on a ticket
     WAITING_FOR_HUMAN moves it to VERIFYING or ACTIVE), and
  3. be capable of producing a LearningSignal (see app.learning).

Not yet implemented: depends on ticket_service + models being backed by
real persistence instead of seed data.
"""


def guide(ticket_id: str, guidance: str) -> None:
    raise NotImplementedError


def approve(ticket_id: str, operator: str) -> None:
    raise NotImplementedError


def correct(ticket_id: str, correction: str, operator: str) -> None:
    raise NotImplementedError


def override(ticket_id: str, reason: str, operator: str) -> None:
    raise NotImplementedError


def teach(topic: str, knowledge: str, operator: str) -> None:
    """Writes into the Solvable Rulebook — see app.memory.rulebook.add_rule."""
    raise NotImplementedError
