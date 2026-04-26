import json
import os
import time
from typing import Any, Dict, Optional


LOG_DIR = "logs"
TRACE_LOG_FILE = os.path.join(LOG_DIR, "agent_traces.jsonl")


def now_ms() -> int:
    return int(time.time() * 1000)


def duration_ms(start_time: float) -> int:
    return int((time.time() - start_time) * 1000)


def build_trace_item(
    step: str,
    name: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    latency_ms: int,
    success: bool = True,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "step": step,
        "name": name,
        "input": input_data,
        "output": output_data,
        "latency_ms": latency_ms,
        "success": success,
        "error": error,
    }


def write_trace_log(event: Dict[str, Any]) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)

    safe_event = {
        **event,
        "timestamp_ms": now_ms(),
    }

    with open(TRACE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(safe_event, ensure_ascii=False) + "\n")