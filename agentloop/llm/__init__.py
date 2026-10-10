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
# "gateway:<alias>" routes calls through the LLM Gateway, e.g. gateway:smart.
GATEWAY_PREFIX = "gateway:"


def make_client(model: str | None = None) -> LLMClient:
    """Build the configured provider: Gemini directly, or the LLM Gateway.

    With no explicit model, fall back to a lighter model when the default is
    overloaded. An explicit model is never swapped silently.
    """
    if model and model.startswith(GATEWAY_PREFIX):
        from agentloop.llm.gateway import DEFAULT_ALIAS, GatewayClient

        return GatewayClient(model[len(GATEWAY_PREFIX) :] or DEFAULT_ALIAS)

    from agentloop.llm.gemini import GeminiClient

    if model:
        return GeminiClient(model)
    return GeminiClient(DEFAULT_MODEL, fallbacks=FALLBACK_MODELS)
