"""
Production-ready LangGraph workflow for Market Brain Agent.

Architecture:
- StateGraph with 7 nodes
- Hybrid planning (rules + LLM)
- Explicit guardrails
- Full tracing and citations
- Bounded multi-step execution (max 3 steps)

Flow:
  router -> direct OR planner
  planner -> guardrail
  guardrail -> retrieval OR tool OR answer
  retrieval -> planner
  tool -> planner
  answer -> END
  direct -> END
"""

from typing import Any, Dict

from langgraph.graph import END, StateGraph

from nodes import (
    answer_node,
    direct_node,
    guardrail_node,
    planner_node,
    retrieval_node,
    router_node,
    tool_node,
)
from state.agent_state import AgentState


MAX_STEPS = 3


class MarketBrainGraph:
    """
    Production-ready LangGraph workflow for Market Brain Agent.
    
    Public API:
    - invoke(message: str, request_id: str, session_id: str | None) -> dict
    """

    def __init__(self) -> None:
        """Initialize graph with nodes and edges."""
        self._graph = self._build_graph()

    def invoke(
        self,
        message: str,
        request_id: str,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        Execute the agent on a user message.
        
        Args:
            message: User input message
            request_id: Unique request identifier
            session_id: Optional session identifier
            
        Returns:
            Dict with keys:
            - answer: Final generated answer
            - metadata: Response metadata
            - tool_trace: Detailed execution trace
            - citations: Document citations
        """
        result = self._graph.invoke(
            {
                "message": message,
                "request_id": request_id,
                "session_id": session_id,
                "route": "",
                "next_action": "",
                "step_count": 0,
                "max_steps": MAX_STEPS,
                "planner_type": "",
                "planner_reason": "",
                "documents": [],
                "retrieved_context": "",
                "tool_result": {},
                "intermediate_results": [],
                "tool_trace": [],
                "citations": [],
            }
        )

        return {
            "answer": result.get("answer", ""),
            "metadata": result.get("metadata", {}),
            "tool_trace": result.get("tool_trace", []),
            "citations": result.get("citations", []),
        }

    def _build_graph(self) -> Any:
        """
        Build LangGraph StateGraph.
        
        Nodes:
        - router: Route to agent or direct
        - planner: Hybrid planner
        - guardrail: Safety validation
        - retrieval: FAISS retrieval
        - tool: Tool execution
        - answer: Answer generation
        - direct: Out-of-domain response
        
        Edges:
        - router -> planner (conditional)
        - router -> direct (conditional)
        - planner -> guardrail
        - guardrail -> retrieval/tool/answer (conditional)
        - retrieval -> planner
        - tool -> planner
        - answer -> END
        - direct -> END
        """
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("router", router_node)
        graph.add_node("planner", planner_node)
        graph.add_node("guardrail", guardrail_node)
        graph.add_node("retrieval", retrieval_node)
        graph.add_node("tool", tool_node)
        graph.add_node("answer", answer_node)
        graph.add_node("direct", direct_node)

        # Set entry point
        graph.set_entry_point("router")

        # Router edges: route -> agent OR direct
        graph.add_conditional_edges(
            "router",
            self._route_after_router,
            {
                "agent": "planner",
                "direct": "direct",
            },
        )

        # Planner flow: planner -> guardrail
        graph.add_edge("planner", "guardrail")

        # Guardrail edges: guardrail -> retrieval/tool/answer
        graph.add_conditional_edges(
            "guardrail",
            self._route_after_guardrail,
            {
                "retrieval": "retrieval",
                "tool": "tool",
                "answer": "answer",
            },
        )

        # Loop back: retrieval/tool -> planner
        graph.add_edge("retrieval", "planner")
        graph.add_edge("tool", "planner")

        # Terminal edges
        graph.add_edge("answer", END)
        graph.add_edge("direct", END)

        return graph.compile()

    def _route_after_router(self, state: AgentState) -> str:
        """Determine next node after router: agent or direct."""
        return "agent" if state.get("route") == "agent" else "direct"

    def _route_after_guardrail(self, state: AgentState) -> str:
        """Determine next node after guardrail: retrieval, tool, or answer."""
        next_action = state.get("next_action", "answer")
        return next_action if next_action in {"retrieval", "tool", "answer"} else "answer"


# Singleton instance
_graph_instance = MarketBrainGraph()


def get_graph() -> MarketBrainGraph:
    """Get singleton graph instance."""
    return _graph_instance
