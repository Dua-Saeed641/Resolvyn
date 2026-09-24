"""Shared LLM types and prompt formatting."""


class LLMUnavailable(RuntimeError):
    """Raised when no configured model can serve the request.

    Callers fall back to deterministic behaviour (docs/claude.md: the prototype
    must run without a real LLM).
    """


# Qwen3.x chat template with thinking switched off: the assistant turn starts
# with an empty <think></think> block, so the model answers immediately.
NO_THINK = "<think>\n\n</think>\n\n"


def to_chatml(messages: list[dict], *, no_think: bool = True) -> str:
    parts = []
    for m in messages:
        parts.append(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n")
    parts.append("<|im_start|>assistant\n" + (NO_THINK if no_think else ""))
    return "".join(parts)
