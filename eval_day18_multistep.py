import uuid
from pprint import pprint

from agent_graph import agent_graph


CASES = [
    {
        "name": "rag_then_answer",
        "message": "According to the docs, what customer segments should we use for dog food campaigns?",
        "expected_route": "langgraph_hybrid_multistep_agent",
        "expected_min_steps": 1,
    },
    {
        "name": "tool_then_answer",
        "message": "Create draft for a premium dog food campaign for high-value customers",
        "expected_route": "langgraph_hybrid_multistep_agent",
        "expected_min_steps": 1,
    },
    {
        "name": "direct_guardrail",
        "message": "What is the weather today?",
        "expected_route": "langgraph_direct",
        "expected_min_steps": 0,
    },
]


def run_case(case: dict) -> bool:
    result = agent_graph.invoke(
        message=case["message"],
        request_id=str(uuid.uuid4()),
        session_id="day18-eval-session",
    )

    metadata = result.get("metadata", {})
    trace = result.get("tool_trace", [])

    route_ok = metadata.get("route") == case["expected_route"]
    step_ok = metadata.get("step_count", 0) >= case["expected_min_steps"]
    max_step_ok = metadata.get("step_count", 0) <= metadata.get("max_steps", 3)
    trace_ok = metadata.get("route") == "langgraph_direct" or len(trace) > 0

    passed = route_ok and step_ok and max_step_ok and trace_ok

    print("\n===", case["name"], "===")
    pprint(
        {
            "passed": passed,
            "route": metadata.get("route"),
            "step_count": metadata.get("step_count"),
            "max_steps": metadata.get("max_steps"),
            "trace_count": metadata.get("trace_count"),
            "planner_type": metadata.get("planner_type"),
            "planner_reason": metadata.get("planner_reason"),
            "citations_count": len(result.get("citations", [])),
            "answer_preview": result.get("answer", "")[:180],
        }
    )

    return passed


def main() -> None:
    passed_count = 0

    for case in CASES:
        if run_case(case):
            passed_count += 1

    print(f"\nDay 18 eval: {passed_count}/{len(CASES)} passed")


if __name__ == "__main__":
    main()