# AgentLoop

A command-line coding agent written from scratch in Python. No LangChain, no agent framework: the loop, tools, safety layer and evaluation are all built by hand.

> Status: **Phase 1, the bare loop.** The agent can read files and answer questions about a repo. Editing, tests and evals come in later phases.

## Install and run

```bash
pip install -e ".[dev]"
export GEMINI_API_KEY=...        # PowerShell: $env:GEMINI_API_KEY="..."
agentloop run "what does utils.py do?" --repo examples/demo_repo
```

Get a free Gemini key at https://aistudio.google.com/apikey. Choose a different model with `--model` or `AGENTLOOP_MODEL`.

## How the loop works

```
task ──► [system prompt + history] ──► LLMClient.chat()
                ▲                            │
                │                  tool calls? ── no ──► final answer
                │                            │ yes
                └──── tool results ◄── run each tool (validated, sandboxed)
```

One step means one model call. The run stops when the model answers in plain text, or when it hits the hard step limit (25 by default).

## Layout

| Path | What it does |
| --- | --- |
| `agentloop/cli.py` | typer commands (`run`, `version`) |
| `agentloop/loop.py` | the agent loop; emits events to observers |
| `agentloop/llm/` | `LLMClient` interface, Gemini provider, scripted fake for tests |
| `agentloop/tools/` | `Tool` base class (pydantic args → JSON schema) and `read_file` |
| `agentloop/safety.py` | `Workspace`: every path must stay inside the repo |
| `agentloop/runlog.py` | writes each step to `runs/<run-id>.jsonl` |
| `prompts/system_v1.md` | versioned system prompt |
| `tests/` | unit tests using `FakeLLMClient`, no network needed |

## Design decisions so far

- **Provider-neutral messages.** The loop never imports a provider SDK. Gemini's raw reply is passed back verbatim, so features like thought signatures keep working.
- **Tool errors go to the model, not to a crash.** Bad arguments, unknown tools and paths outside the repo come back as an `Error: ...` tool result explaining how to fix the call.
- **Schemas come from pydantic.** They are simplified (no `anyOf`/`null`/`title`) so every provider accepts them.
- **Output is capped** at 200 lines per tool call, and the result says how to read the rest.

## Tests

```bash
pytest
```

## Roadmap

1. ✅ Bare loop: `read_file`, step limit, JSONL logs
2. Toolset: `list_files`, `search_code`, `edit_file`, `create_file`, `run_tests`, `git_diff`, plus a 5-task eval harness
3. Safety: approval diffs, command allowlist, budgets, pytest timeout, clean-repo check
4. Context management: token counting and trimming of old tool output
5. Plan mode, test-checked completion, test-file and config write protection, loop detection
6. Full 20-task benchmark, v1 vs v2 experiment, demo GIF
