# Pydantic AI Streaming Regression Replay

This repository supports EarlyAI's historical replay of a streaming regression introduced in Pydantic AI v1.92.0 and fixed in v1.106.0.

Pydantic did not sponsor or participate in this replay and is not presented as an EarlyAI customer. The repository is based on the open-source [Pydantic AI project](https://github.com/pydantic/pydantic-ai).

## What Failed

The affected path required a caller to provide an `event_stream_handler` that returned before consuming the full event stream. Before v1.92.0, Pydantic AI drained the remaining events after the handler returned. In v1.92.0 through v1.105.0, the remaining events were not drained, which could leave the assembled `ModelResponse` incomplete.

With real providers, users reported incomplete or empty responses, missing tool calls, and under-reported token usage. In this offline reproduction, the empty response causes `UnexpectedModelBehavior` after output retries are exhausted.

## Run the Reproduction

The script uses Pydantic AI's deterministic offline `TestModel`. It requires [uv](https://docs.astral.sh/uv/) but no API key or external model call.

From the repository root, run:

```bash
uv run --isolated --no-project --with "pydantic-ai-slim==1.91.0" python pydantic-ai-repro.py
uv run --isolated --no-project --with "pydantic-ai-slim==1.92.0" python pydantic-ai-repro.py
uv run --isolated --no-project --with "pydantic-ai-slim==1.106.0" python pydantic-ai-repro.py
```

Each command runs the same prompt twice:

1. Once without an event-stream handler.
2. Once with a handler that consumes the first event and then returns.
3. The script compares the returned output and token usage.

## Expected Results

| Version | Expected result | Observed behavior |
|---|---|---|
| v1.91.0 | Pass | Output and usage match with and without the handler |
| v1.92.0 | Fail | The partial-consuming handler leaves an empty response and triggers retry exhaustion |
| v1.106.0 | Pass | Output and usage match after stream draining is restored |

The process exits with status `0` for a pass and `1` for the affected behavior.

## How the Code Changed

The introducing change was part of a broader cancellation cleanup. It removed a drain loop from the normal completion path. When a supplied handler returned early, the rest of the stream was no longer consumed.

The later fix restored draining after the handler returned and added regression coverage in `tests/test_streaming.py`.

Inspect the relevant history:

- [v1.91.0 to v1.92.0 release comparison](https://github.com/pydantic/pydantic-ai/compare/v1.91.0...v1.92.0)
- [PR #5313: cancellation cleanup](https://github.com/pydantic/pydantic-ai/pull/5313)
- [Issue #5769: incomplete streamed responses](https://github.com/pydantic/pydantic-ai/issues/5769)
- [PR #5771: streaming fix](https://github.com/pydantic/pydantic-ai/pull/5771)
- [v1.105.0 to v1.106.0 fix comparison](https://github.com/pydantic/pydantic-ai/compare/v1.105.0...v1.106.0)

## What This Reproduction Proves

The script establishes that the selected handler behavior passes in v1.91.0, fails in v1.92.0, and passes again in v1.106.0. It independently reproduces the defect described by the later upstream issue and the behavior restored by the fix.

It does not rerun Regression Guard, reproduce EarlyAI's proprietary analysis, estimate detection performance across arbitrary releases, or establish that every regression would be detected.

Read the full [EarlyAI Regression Case File](https://www.startearly.ai/regression-case-files/pydantic-ai-release-replay/) for the historical replay, Regression Guard finding, methodology, and limitations.
