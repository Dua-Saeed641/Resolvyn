"""Knowledge base — docs/architecture.md §2.6 (common-query memory), §6."""

from fastapi import APIRouter

from data.seed_data import KNOWLEDGE_DOCUMENTS

router = APIRouter()


@router.get("")
def list_knowledge_documents():
    return KNOWLEDGE_DOCUMENTS
