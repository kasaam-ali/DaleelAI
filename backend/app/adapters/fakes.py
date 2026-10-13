from app.core.ports import ChatMessage, LLMResult, Role


class FakeLLM:
    def __init__(self, reply: str = "fake answer"):
        self.reply = reply
        self.calls: list[tuple[Role, list[ChatMessage]]] = []

    async def complete(
        self,
        role: Role,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResult:
        self.calls.append((role, messages))
        return LLMResult(text=self.reply, model="fake/fake", fallback=False, latency_ms=0)
