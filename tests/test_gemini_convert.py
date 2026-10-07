"""Message conversion for the Gemini provider, tested without network calls."""

from google.genai import types

from agentloop.llm.base import Message, ToolCall
from agentloop.llm.gemini import from_gemini_response, to_gemini_contents


def test_converts_conversation_and_groups_tool_results():
    messages = [
        Message("system", "be helpful"),
        Message("user", "read two files"),
        Message("assistant", "", tool_calls=[ToolCall("a", "read_file", {"path": "x"}), ToolCall("b", "read_file", {"path": "y"})]),
        Message("tool", "X", tool_call_id="a", name="read_file"),
        Message("tool", "Y", tool_call_id="b", name="read_file"),
    ]
    system, contents = to_gemini_contents(messages)
    assert system == "be helpful"
    assert [c.role for c in contents] == ["user", "model", "user"]
    assert [p.function_call.name for p in contents[1].parts] == ["read_file", "read_file"]
    responses = [p.function_response for p in contents[2].parts]
    assert [r.id for r in responses] == ["a", "b"]
    assert responses[0].response == {"result": "X"}


def test_raw_model_content_is_sent_back_verbatim():
    raw = types.Content(role="model", parts=[types.Part(text="hi", thought_signature=b"sig")])
    _, contents = to_gemini_contents([Message("user", "q"), Message("assistant", "hi", raw=raw)])
    assert contents[1] is raw


def test_parses_function_calls_text_and_usage():
    resp = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(text="thinking...", thought=True),
                        types.Part(text="Let me look."),
                        types.Part(function_call=types.FunctionCall(name="read_file", args={"path": "a.py"})),
                    ],
                )
            )
        ],
        usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=100, candidates_token_count=7),
    )
    out = from_gemini_response(resp)
    assert out.text == "Let me look."
    assert out.tool_calls[0].name == "read_file"
    assert out.tool_calls[0].arguments == {"path": "a.py"}
    assert out.tool_calls[0].id.startswith("call_")
    assert (out.usage.input_tokens, out.usage.output_tokens) == (100, 7)
