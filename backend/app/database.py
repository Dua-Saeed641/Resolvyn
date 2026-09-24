"""SQLite session/engine setup (docs/architecture.md §3, prototype database).

Tables mirror project.md §39: customers, tickets, messages, agents,
agent_events, tool_calls, knowledge_documents, human_actions, learning_signals.
"""

from sqlmodel import SQLModel, Session, create_engine

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Create tables for all imported SQLModel models."""
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
