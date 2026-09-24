"""Perception Layer — docs/architecture.md §1, layer 2.

Multimodal Processor + Pre-processing & Enrichment: turns a raw inbound
message (text/voice/image, any channel) into a normalized, enriched
payload for the Judgment layer. In the prototype this also covers the
call-liveness classifier and language routing described in
docs/architecture.md §2.1 (Hindi/English native, Gnani AI fallback).

Not yet implemented — requires an LLM or speech provider to be configured
(app.config.Settings.llm_api_key). Without one, callers should fall back
to deterministic mock enrichment (project.md §87).
"""

from typing import TypedDict


class EnrichedMessage(TypedDict):
    text: str
    language: str
    channel: str


def enrich(raw_text: str, channel: str) -> EnrichedMessage:
    """Normalize + language-detect a raw inbound message.

    Deterministic stub: assumes English and passes the text through
    unchanged until real language detection is wired up.
    """
    return {"text": raw_text.strip(), "language": "en", "channel": channel}
