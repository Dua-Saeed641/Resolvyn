"""SQLModel table definitions — project.md §39-44.

Importing this package registers every table with SQLModel.metadata so
app.database.init_db() can create them.
"""

from app.models.agent import Agent
from app.models.agent_event import AgentEvent
from app.models.customer import Customer
from app.models.human_action import HumanAction
from app.models.knowledge_document import KnowledgeDocument
from app.models.learning_signal import LearningSignal
from app.models.message import Message
from app.models.ticket import Ticket
from app.models.tool_call import ToolCall

__all__ = [
    "Agent",
    "AgentEvent",
    "Customer",
    "HumanAction",
    "KnowledgeDocument",
    "LearningSignal",
    "Message",
    "Ticket",
    "ToolCall",
]
