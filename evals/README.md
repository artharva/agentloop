# Benchmark

20 small, self-contained buggy Python projects: 8 easy, 8 medium, 4 hard.
`tests/test_benchmark.py` checks every task: its visible tests fail on the buggy
code, and the reference solution passes both visible and hidden tests.

| Level | Tasks |
| --- | --- |
| Easy | off-by-one (e01, e05), wrong comparison (e02, e06), missing return (e03, e07), wrong default argument (e04, e08) |
| Medium | bug across 2 files (m01, m08), missing validation (m02, m05), wrong exception handling (m03, m06), small feature (m04, m07) |
| Hard | root cause 3+ files away (h01), misleading error message (h02), refactor that must stay green (h03), two interacting bugs behind a service (h04) |

## Task layout

```
evals/tasks/<id>/
  task.md        instruction given to the agent
  task.json      {"difficulty": "easy|medium|hard", "allow_test_edits": false}
  repo/          buggy code + visible tests: the only thing the agent sees
  hidden_tests/  extra tests used only for judging
  solution/      reference fix, used only to validate the task
```

## Running

```bash
agentloop eval --version v1 --model gemini-flash-lite-latest --repeat 3
agentloop eval --version v2 --model gemini-flash-lite-latest --repeat 3 --prompt prompts/system_v2.md
agentloop compare evals/results/v1.csv evals/results/v2.csv
```

Each run writes `evals/results/<version>.csv` (one row per task and run) and
`evals/results/<version>_failures.md` (a failure log with a detected reason per
failed task, plus a Notes column for you). Per-task JSONL logs go to `runs/evals/`.

Pin `--model` so that runs compare like for like; without it, AgentLoop may
fall back to a lighter model when Gemini is overloaded. On the free tier,
`--min-interval 5` spaces out calls to stay under the rate limit.
