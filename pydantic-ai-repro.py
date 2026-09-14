"""Reproduce the Pydantic AI streaming regression reported in issue #5769.

Run the same prompt twice against the offline TestModel: once without an
event_stream_handler and once with a handler that consumes only the first
event. On unaffected versions, both runs return identical output and usage.
On affected versions, the handler run returns a truncated or empty result.
With TestModel, this surfaces as an UnexpectedModelBehavior exception.

Exit code 0 means the behavior passed. Exit code 1 means it failed.
"""

import asyncio
import sys
import warnings

import pydantic_ai
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

agent = Agent(TestModel())


async def partial_handler(ctx, stream):
    """Consume the first event, then return before the stream is complete."""
    async for _event in stream:
        break


def get_usage(result):
    """Support Pydantic AI versions where usage is a method or a property."""
    attr = result.usage
    if callable(attr):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore',
                message=r'`AgentRunResult\.usage` is no longer a method.*',
            )
            return attr()
    return attr


async def main():
    """Compare baseline and partial-handler behavior for the installed version."""
    version = pydantic_ai.__version__
    baseline = await agent.run('hello')
    baseline_usage = get_usage(baseline)
    print(f'version={version}')
    print(f'baseline    : output={baseline.output!r} usage={baseline_usage}')

    try:
        with_handler = await agent.run('hello', event_stream_handler=partial_handler)
    except Exception as exc:
        print(f'with_handler: RAISED {type(exc).__name__}: {exc}')
        print(
            f'RESULT: FAIL version={version} mode=exception '
            '(partial-consuming handler crashed the run; empty response '
            'triggered retry exhaustion)'
        )
        sys.exit(1)

    handler_usage = get_usage(with_handler)
    print(f'with_handler: output={with_handler.output!r} usage={handler_usage}')
    same_output = with_handler.output == baseline.output
    same_usage = (
        handler_usage.input_tokens,
        handler_usage.output_tokens,
    ) == (
        baseline_usage.input_tokens,
        baseline_usage.output_tokens,
    )
    if same_output and same_usage:
        print(f'RESULT: PASS version={version} (output and usage identical with and without handler)')
        sys.exit(0)

    print(f'RESULT: FAIL version={version} mode=silent (output_equal={same_output} usage_equal={same_usage})')
    sys.exit(1)


asyncio.run(main())
