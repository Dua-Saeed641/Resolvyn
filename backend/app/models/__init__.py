"""SQLModel table definitions — project.md §39-44 + memory tables.

Importing this package registers every table with SQLModel.metadata so
app.database.init_db() can create them.
"""

from app.models.agent import Agent
from app.models.agent_event import AgentEvent
from app.models.customer import Customer
from app.models.human_action import HumanAction
from app.models.knowledge_document import KnowledgeDocument
from app.models.learning_signal import LearningSignal
from app.models.memory import FirstTimeBug, KgEdge, KgNode, MemoryChunk, RulebookEntry
from app.models.message import Message
from app.models.pending_action import PendingAction
from app.models.refund import Refund
from app.models.ticket import Ticket
from app.models.tool_call import ToolCall

__all__ = [
    "Refund",
    "Agent",
    "AgentEvent",
    "Customer",
    "FirstTimeBug",
    "HumanAction",
    "KgEdge",
    "KgNode",
    "KnowledgeDocument",
    "LearningSignal",
    "MemoryChunk",
    "Message",
    "PendingAction",
    "RulebookEntry",
    "Ticket",
    "ToolCall",
]
