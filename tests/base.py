class FakeGeminiClient:
    """Test double for GeminiClient — returns a canned answer; records prompts."""

    def __init__(self, answer: str = "fake-answer") -> None:
        self.answer = answer
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer
