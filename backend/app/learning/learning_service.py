"""Analytics & Learning Loop — docs/architecture.md §1 layer 9, §2.6.

Prototype scope only (project.md §29, §90): a learning signal is recorded
whenever the AI's expected action diverges from the observed/human
action. Presented as a "prediction-error-style event" — never claim a
reinforcement-learning model was actually retrained.
"""


def record_signal(
    ticket_id: str,
    signal_type: str,
    expected_action: str,
    observed_action: str,
    source_event: str | None = None,
) -> None:
    raise NotImplementedError("Wire up to app.models.learning_signal once persistence exists.")
