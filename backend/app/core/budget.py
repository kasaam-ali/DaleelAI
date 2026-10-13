"""Hard cap on LLM calls for one question. A cache hit is not a call."""


class CallBudgetExceeded(Exception):
    def __init__(self, cap: int):
        super().__init__(f"LLM call cap is {cap}")
        self.cap = cap


class CallBudget:
    def __init__(self, cap: int = 5):
        if cap < 1:
            raise ValueError("cap must be at least 1")
        self.cap = cap
        self.used = 0

    def remaining(self) -> int:
        return self.cap - self.used

    def charge(self) -> None:
        if self.used >= self.cap:
            raise CallBudgetExceeded(self.cap)
        self.used += 1
