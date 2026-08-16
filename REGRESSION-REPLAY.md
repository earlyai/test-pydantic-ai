# Pydantic AI Streaming Regression Replay

This repository supports EarlyAI's historical replay of a streaming regression introduced in Pydantic AI v1.92.0 and fixed in v1.106.0.

It provides two ways to inspect the case:

1. Give Early's generated investigation prompt to Claude Code or Codex and ask it to verify the finding against the repository.
2. Run the deterministic offline reproduction across the release before the regression, the affected release, and the fixed release.

Pydantic did not sponsor or participate in this replay and is not presented as an EarlyAI customer. The repository is based on the open-source [Pydantic AI project](https://github.com/pydantic/pydantic-ai).

## Before You Start

You need:

- Git
- Claude Code or Codex for the code and history investigation
- [uv](https://docs.astral.sh/uv/) for the runtime reproduction

The runtime reproduction uses Pydantic AI's offline `TestModel`. It requires no model API key or external model call.

## Clone the Repository

```bash
git clone https://github.com/earlyai/test-pydantic-ai.git
cd test-pydantic-ai
git fetch --tags
```

The investigation compares the `v1.91.0` base tag with the `v1.92.0` head tag. The later `v1.106.0` tag contains the upstream fix.

## Verify Early's Finding

Early's historical Regression Guard run generated a finding titled **Removed forced drain truncates usage on early exit**. It also generated an investigation prompt that packages the finding, its initial assessment, and a protocol for independently checking every claim against the code and Git history.

The prompt is available in [`early-regression-investigation-prompt.md`](early-regression-investigation-prompt.md).

Start one of the supported coding agents from the repository root:

```bash
# Option 1: Claude Code
claude

# Option 2: Codex
codex
```

In the coding-agent session, submit:

```text
Read early-regression-investigation-prompt.md and carry out the investigation exactly as written. Verify every claim against this local repository and cite the files, lines, commits, and tags that support your conclusion.
```

You can also open the prompt file and paste its full contents into the session.

### Expected Investigation Result

The wording may differ between agents, but a supported result should establish these facts from the repository:

- **Classification:** REGRESSION. Behavior worsened between v1.91.0 and v1.92.0.
- **Introducing commit:** `93a61042943d3887c737ba753b908f258e8ea162`, “fix: Clean up streaming responses on cancellation (#5313),” committed on May 8, 2026.
- **Mechanism:** removing the normal-path drain loop meant that a supplied `event_stream_handler` could return before the remaining stream was consumed, leaving the assembled response and usage incomplete.
- **Affected path:** callers supplying an event-stream handler that returned before consuming the full stream. The default path without a handler still drained the stream.
- **State at the analyzed head:** the defect remained present at v1.92.0.
- **Later fix:** `49f62a386041abd6e0d960dd629c3b4fe28eac63`, released in v1.106.0, restored draining after the handler returned.
- **Minimal remedy:** restore stream draining on normal completion and cover the partial-consuming handler condition with a regression test.

Require the coding agent to show its evidence. Do not accept a conclusion based only on the finding text supplied in the prompt.

This is an independent verification of an Early finding, not a blind recreation of the original Regression Guard run. The prompt begins with the finding and asks the coding agent to confirm, refute, or correct it.

## Reproduce the Runtime Failure

From the repository root, run:

```bash
uv run --isolated --no-project --no-config --with "pydantic-ai-slim==1.91.0" python pydantic-ai-repro.py
uv run --isolated --no-project --no-config --with "pydantic-ai-slim==1.92.0" python pydantic-ai-repro.py
uv run --isolated --no-project --no-config --with "pydantic-ai-slim==1.106.0" python pydantic-ai-repro.py
```

Each command runs the same model prompt twice:

1. Once without an event-stream handler.
2. Once with a handler that consumes the first event and then returns.
3. The script compares the returned output and token usage.

## Expected Runtime Results

| Version | Expected result | Observed behavior |
|---|---|---|
| v1.91.0 | Pass | Output and usage match with and without the handler |
| v1.92.0 | Fail | The partial-consuming handler leaves an empty response and triggers retry exhaustion |
| v1.106.0 | Pass | Output and usage match after stream draining is restored |

The process exits with status `0` for a pass and `1` for the affected behavior.

## What Failed

The affected path required a caller to provide an `event_stream_handler` that returned before consuming the full event stream. Before v1.92.0, Pydantic AI drained the remaining events after the handler returned. In v1.92.0 through v1.105.0, the remaining events were not drained, which could leave the assembled `ModelResponse` incomplete.

With real providers, users reported incomplete or empty responses, missing tool calls, and under-reported token usage. In this offline reproduction, the empty response causes `UnexpectedModelBehavior` after output retries are exhausted.

## How the Evidence Fits Together

The two exercises test different parts of the case:

- The Early-generated prompt asks a coding agent to verify the code change, reachability, introduction point, severity, and remedy against the repository.
- The Python script demonstrates the affected runtime behavior against published Pydantic AI packages.
- The later upstream issue and fix independently confirm the same mechanism.

Inspect the primary history:

- [v1.91.0 to v1.92.0 release comparison](https://github.com/pydantic/pydantic-ai/compare/v1.91.0...v1.92.0)
- [PR #5313: cancellation cleanup](https://github.com/pydantic/pydantic-ai/pull/5313)
- [Issue #5769: incomplete streamed responses](https://github.com/pydantic/pydantic-ai/issues/5769)
- [PR #5771: streaming fix](https://github.com/pydantic/pydantic-ai/pull/5771)
- [v1.105.0 to v1.106.0 fix comparison](https://github.com/pydantic/pydantic-ai/compare/v1.105.0...v1.106.0)

## What This Replay Proves

The investigation prompt gives Claude or Codex the exact finding Early generated and requires it to verify that finding against the local repository. The runtime script establishes that the selected handler behavior passes in v1.91.0, fails in v1.92.0, and passes again in v1.106.0.

Together, they let readers audit the code-level finding and reproduce the defect and fix. They do not rerun Regression Guard, recreate the original detection process, estimate detection performance across arbitrary releases, or establish that every regression would be detected.

Read the full [EarlyAI Regression Case File](https://www.startearly.ai/regression-case-files/pydantic-ai-release-replay/) for the historical replay, Regression Guard finding, methodology, and limitations.
