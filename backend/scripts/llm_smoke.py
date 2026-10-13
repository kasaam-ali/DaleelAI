"""Calls every LLM role once and prints which model answered.

Run: docker compose run --rm --no-deps backend python -m scripts.llm_smoke
"""

import asyncio

from app.adapters.llm_litellm import LiteLLMGateway
from app.core.ports import AllProvidersUnavailable, ChatMessage
from app.settings import load_models_config

PROMPT = [ChatMessage(role="user", content="Reply with the single word OK.")]


async def main() -> None:
    config = load_models_config()
    gateway = LiteLLMGateway(config)
    for role in config.roles:
        try:
            result = await gateway.complete(role, PROMPT)
        except AllProvidersUnavailable as error:
            print(f"{role:<10} FAILED  {'; '.join(error.errors)}")
            continue
        print(
            f"{role:<10} {result.model:<36} fallback={result.fallback} "
            f"{result.latency_ms} ms  reply={result.text.strip()!r}"
        )


if __name__ == "__main__":
    asyncio.run(main())
