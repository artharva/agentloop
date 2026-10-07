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

DEFAULT_MODEL = "gemini-2.5-flash"


def make_client(model: str | None = None) -> LLMClient:
    """Build the configured provider. Only Gemini exists in Phase 1."""
    from agentloop.llm.gemini import GeminiClient

    return GeminiClient(model or DEFAULT_MODEL)
