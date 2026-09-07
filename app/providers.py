import os
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class LLMResult:
    output: str
    model: str
    provider: str
    usage: dict[str, Any]


class LLMProvider(Protocol):
    def ready(self) -> None: ...
    def chat(self, prompt: str, model: str | None, max_output_tokens: int, temperature: float) -> LLMResult: ...


class MockProvider:
    def ready(self) -> None:
        return None

    def chat(self, prompt: str, model: str | None, max_output_tokens: int, temperature: float) -> LLMResult:
        del temperature
        selected_model = model or "mock-model"
        output = f"Mock response: {prompt[:200]}"
        return LLMResult(
            output=output,
            model=selected_model,
            provider="mock",
            usage={
                "input_tokens": max(1, len(prompt) // 4),
                "output_tokens": min(max_output_tokens, max(1, len(output) // 4)),
            },
        )


class OpenAIProvider:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.default_model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
        self.timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed") from exc

        self.client = OpenAI(api_key=self.api_key, timeout=self.timeout, max_retries=0)

    def ready(self) -> None:
        if not self.api_key:
            raise RuntimeError("missing provider credentials")

    def chat(self, prompt: str, model: str | None, max_output_tokens: int, temperature: float) -> LLMResult:
        selected_model = model or self.default_model
        response = self.client.responses.create(
            model=selected_model,
            input=prompt,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )
        usage_obj = getattr(response, "usage", None)
        usage = {
            "input_tokens": getattr(usage_obj, "input_tokens", 0) if usage_obj else 0,
            "output_tokens": getattr(usage_obj, "output_tokens", 0) if usage_obj else 0,
            "total_tokens": getattr(usage_obj, "total_tokens", 0) if usage_obj else 0,
        }
        return LLMResult(
            output=response.output_text,
            model=selected_model,
            provider="openai",
            usage=usage,
        )
