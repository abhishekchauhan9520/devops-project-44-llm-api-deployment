import os
import time
import uuid
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .providers import LLMProvider, MockProvider, OpenAIProvider

app = FastAPI(title="Production LLM API", version="1.0.0")

MAX_PROMPT_CHARS = int(os.getenv("MAX_PROMPT_CHARS", "12000"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1024"))
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"
SERVICE_API_KEY = os.getenv("SERVICE_API_KEY")

_PROVIDER: LLMProvider | None = None


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=MAX_PROMPT_CHARS)
    model: str | None = None
    max_output_tokens: int = Field(default=512, ge=1, le=MAX_OUTPUT_TOKENS)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class ChatResponse(BaseModel):
    request_id: str
    model: str
    provider: str
    output: str
    usage: dict[str, Any]
    latency_ms: int


def provider() -> LLMProvider:
    global _PROVIDER
    if _PROVIDER is None:
        selected = os.getenv("LLM_PROVIDER", "mock").lower()
        if selected == "openai":
            _PROVIDER = OpenAIProvider()
        elif selected == "mock":
            _PROVIDER = MockProvider()
        else:
            raise RuntimeError(f"Unsupported LLM_PROVIDER: {selected}")
    return _PROVIDER


def authorize(x_api_key: str | None) -> None:
    if not REQUIRE_API_KEY:
        return
    if not SERVICE_API_KEY or x_api_key != SERVICE_API_KEY:
        raise HTTPException(status_code=401, detail="invalid API key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    try:
        provider().ready()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"status": "ready"}


@app.post("/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest, x_api_key: str | None = Header(default=None)) -> ChatResponse:
    authorize(x_api_key)
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    result = provider().chat(request.prompt, request.model, request.max_output_tokens, request.temperature)
    latency_ms = int((time.perf_counter() - started) * 1000)
    return ChatResponse(
        request_id=request_id,
        model=result.model,
        provider=result.provider,
        output=result.output,
        usage=result.usage,
        latency_ms=latency_ms,
    )
