from agentloop.llm.base import (
    LLMClient,
    LLMError,
    Message,
    Response,
    ToolCall,
    ToolSpec,
    Usage,
)

__all__ = [
    "LLMClient",
    "LLMError",
    "Message",
    "Response",
    "ToolCall",
    "ToolSpec",
    "Usage",
    "make_client",
]

# "-latest" aliases track Google's current Flash models, so the default does
# not break when a pinned version is retired. Pin a version with --model for
# eval runs that must be reproducible.
DEFAULT_MODEL = "gemini-flash-latest"
FALLBACK_MODELS = ["gemini-flash-lite-latest"]


def make_client(model: str | None = None) -> LLMClient:
    """Build the configured provider. Only Gemini exists in Phase 1.

    With no explicit model, fall back to a lighter model when the default is
    overloaded. An explicit model is never swapped silently.
    """
    from agentloop.llm.gemini import GeminiClient

    if model:
        return GeminiClient(model)
    return GeminiClient(DEFAULT_MODEL, fallbacks=FALLBACK_MODELS)
