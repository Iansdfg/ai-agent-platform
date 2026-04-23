import json
import time
from typing import Any, Dict, List

from core.config import MODEL_NAME
from services.llm_service import LLMService
from tools.registry import ToolRegistry


class Orchestrator:
    def __init__(self) -> None:
        self._llm_service = LLMService()
        self._tool_registry = ToolRegistry()

    def handle_chat(
        self,
        message: str,
        request_id: str,
        session_id: str | None = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        tool_trace: List[Dict[str, Any]] = []
        citations: List[Dict[str, Any]] = []
        route = "direct"

        decision = self._llm_service.decide_tool(
            user_message=message,
            tools=self._tool_registry.list_tools()
        )

        if decision.need_tool and decision.tool_name:
            route = "tool"

            tool_start = time.time()
            try:
                tool_output = self._tool_registry.execute(
                    decision.tool_name,
                    decision.tool_input
                )
                tool_latency_ms = int((time.time() - tool_start) * 1000)

                tool_trace.append(
                    {
                        "tool_name": decision.tool_name,
                        "tool_input": decision.tool_input,
                        "tool_output": tool_output,
                        "latency_ms": tool_latency_ms,
                        "success": True,
                        "error": None,
                    }
                )

                citations = tool_output.get("citations", [])

                tool_result_text = json.dumps(tool_output, ensure_ascii=False, indent=2)
                answer = self._llm_service.generate_final_answer(
                    user_message=message,
                    tool_result=tool_result_text
                )

            except Exception as e:
                tool_latency_ms = int((time.time() - tool_start) * 1000)

                tool_trace.append(
                    {
                        "tool_name": decision.tool_name,
                        "tool_input": decision.tool_input,
                        "tool_output": {},
                        "latency_ms": tool_latency_ms,
                        "success": False,
                        "error": str(e),
                    }
                )

                answer = self._llm_service.generate_final_answer(
                    user_message=message,
                    tool_result=f"Tool execution failed: {str(e)}"
                )
        else:
            answer = self._llm_service.generate_final_answer(
                user_message=message
            )

        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "answer": answer,
            "metadata": {
                "request_id": request_id,
                "model": MODEL_NAME,
                "latency_ms": latency_ms,
                "session_id": session_id,
                "route": route,
                "response_type": "final",
                "tool_decision_reason": decision.reason,
            },
            "tool_trace": tool_trace,
            "citations": citations,
        }