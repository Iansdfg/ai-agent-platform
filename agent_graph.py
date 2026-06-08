"""
Backward-compatible wrapper for Market Brain Agent graph.

This module is now a thin wrapper around the production-ready LangGraph workflow
defined in graphs/market_brain_graph.py.

Legacy imports and usage are maintained for backward compatibility:
    from agent_graph import agent_graph
    result = agent_graph.invoke(message, request_id, session_id)
"""

from graphs.market_brain_graph import MarketBrainGraph

# Singleton instance for backward compatibility with app.py
agent_graph = MarketBrainGraph()

__all__ = ["agent_graph"]
