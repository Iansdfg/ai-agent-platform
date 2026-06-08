"""
Backward compatibility wrapper for AgentState.

This module is deprecated. Import directly from state.agent_state instead:
    from state.agent_state import AgentState
"""

from state.agent_state import AgentState

__all__ = ["AgentState"]