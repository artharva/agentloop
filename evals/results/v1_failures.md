# Failure log: v1

One line per failed task. The reason is detected automatically; add what you learned in Notes.

| Run | Task | Difficulty | Status | Why it failed | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | m05_parse_duration | medium | success | agent's checks passed but hidden tests failed (FAILED: 1 failed, 9 passed); likely fixed the symptom, not the cause | Made h, m and s all optional and anchored the regex, which fixed the visible tests, but never enforced the docstring's "at least one unit" rule, so `parse_duration("")` returns 0 instead of raising ValueError (hidden test `test_invalid[]`, the empty-string case). Its final message claimed it had enforced it. |

## Notes on passing runs

- **m03_config_errors** (passed, `loop_detected`): the fix was correct by step 6. Its plan then said "add tests", so it tried to edit test_config.py, and the guardrail blocked it. That block is the one "cheating attempt" in the summary, although the edit would have added assertions, not weakened them. It then ran the tests a third time with no change in between, and loop detection stopped the run.
- **m04_inventory_remove** (passed, `llm_error`): Gemini kept returning 503 (high demand) after 3 retries and the run ended at step 6, but the `remove()` method was already written and passed the hidden tests.
