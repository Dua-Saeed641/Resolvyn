"""Knowledge & Tools — docs/architecture.md §1 layer 6, §2.6 (common-query
memory, vector half: Business logic / Pure SOPs / Product DB).

Retrieves ranked knowledge documents for a query and reports a similarity
score per project.md §60 ("Knowledge retrieved... Similarity: 0.93").
Never expose raw embeddings to callers.

Not yet implemented: requires a vector store (see memory/memory_engine.py)
seeded from data/seed_data.py's KNOWLEDGE_DOCUMENTS.
"""

from typing import TypedDict


class RetrievedDocument(TypedDict):
    title: str
    similarity: float


def retrieve(query: str, top_k: int = 3) -> list[RetrievedDocument]:
    raise NotImplementedError("Wire up to app.memory.memory_engine once a vector store exists.")
