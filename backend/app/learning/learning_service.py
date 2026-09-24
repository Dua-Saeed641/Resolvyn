"""Learning Signals — docs/architecture.md §1 layer 9, project.md §28-29.

A learning signal is the recorded artifact of a human correction / override /
teaching event (AI decision vs human decision vs reason) or of a resolution. It
is a learning-EVENT concept: nothing here claims a model was retrained
(project.md §29, §90). What actually changes behaviour is the Solvable
Rulebook, which the signal points to.
"""

from sqlmodel import Session, select

from app.database import engine
from app.models import LearningSignal
from app.services.realtime import hub
from app.utils import iso

SIGNAL_TYPES = (
    "Human correction", "Human approval", "Human override", "Human guidance", "Human teaching",
    "First-time bug suggestion", "Wrong agent routing", "Failed tool action", "Policy conflict",
    "Customer rejection", "Successful resolution",
)


def _dict(s: LearningSignal) -> dict:
    return {
        "signal_id": s.signal_id, "code": f"LS-{s.signal_id:04d}", "ticket_id": s.ticket_id,
        "source_event": s.source_event, "signal_type": s.signal_type, "expected_action": s.expected_action,
        "observed_action": s.observed_action, "description": s.description, "timestamp": iso(s.timestamp),
    }


def record(ticket_id: str, signal_type: str, *, source_event: str | None = None, expected: str | None = None,
           observed: str | None = None, description: str | None = None) -> dict:
    with Session(engine, expire_on_commit=False) as s:
        sig = LearningSignal(ticket_id=ticket_id, signal_type=signal_type, source_event=source_event,
                             expected_action=expected, observed_action=observed, description=description)
        s.add(sig)
        s.commit()
    d = _dict(sig)
    hub.to_ops({"type": "learning_signal", "signal": d})
    return d


def list_signals(limit: int = 200) -> list[dict]:
    with Session(engine) as s:
        rows = s.exec(select(LearningSignal).order_by(LearningSignal.signal_id.desc()).limit(limit)).all()
    return [_dict(r) for r in rows]
