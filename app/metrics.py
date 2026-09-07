import threading
import time
from collections import defaultdict

_lock = threading.Lock()
_request_count = 0
_error_count = 0
_latency_sum_ms = 0
_token_count: dict[str, int] = defaultdict(int)


def record_request(model: str, latency_ms: int, error: bool, usage: dict) -> None:
    global _request_count, _error_count, _latency_sum_ms
    with _lock:
        _request_count += 1
        _latency_sum_ms += latency_ms
        if error:
            _error_count += 1
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            value = int(usage.get(key, 0) or 0)
            _token_count[(model, key)] += value


def render_prometheus() -> str:
    with _lock:
        lines = [
            "# HELP llm_api_requests_total Total LLM API requests.",
            "# TYPE llm_api_requests_total counter",
            f"llm_api_requests_total {_request_count}",
            "# HELP llm_api_errors_total Total LLM API errors.",
            "# TYPE llm_api_errors_total counter",
            f"llm_api_errors_total {_error_count}",
            "# HELP llm_api_request_latency_ms_sum Sum of request latency in milliseconds.",
            "# TYPE llm_api_request_latency_ms_sum counter",
            f"llm_api_request_latency_ms_sum {_latency_sum_ms}",
        ]
        for (model, token_type), value in sorted(_token_count.items()):
            safe_model = model.replace('"', '')
            lines.extend([
                "# TYPE llm_api_tokens_total counter" if token_type == "input_tokens" else "",
                f'llm_api_tokens_total{{model="{safe_model}",type="{token_type}"}} {value}',
            ])
        return "\n".join(line for line in lines if line) + "\n"
