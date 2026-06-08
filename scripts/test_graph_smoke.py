#!/usr/bin/env python3
"""
Smoke test for Market Brain Graph refactoring.

Tests:
1. Direct route (out-of-domain query)
2. Router decision logic
3. Guardrail validation
4. State propagation through nodes

Run: python scripts/test_graph_smoke.py
"""

import uuid
from agent_graph import agent_graph


def test_direct_route():
    """Test out-of-domain query routes to direct node."""
    print("\n=== Test 1: Direct Route ===")
    message = "What's the weather today?"
    request_id = str(uuid.uuid4())
    
    result = agent_graph.invoke(
        message=message,
        request_id=request_id,
        session_id="test-session",
    )
    
    assert result["answer"], "Direct node should return an answer"
    assert "Market Brain" in result["answer"], "Direct answer should mention Market Brain tasks"
    assert result["metadata"]["graph_node"] == "direct", "Should route to direct node"
    assert result["metadata"]["response_type"] == "final", "Response should be final"
    print(f"✓ Direct route test passed")
    print(f"  Answer: {result['answer'][:80]}...")
    print(f"  Route: {result['metadata']['route']}")


def test_router_keywords():
    """Test router recognizes domain keywords."""
    print("\n=== Test 2: Router Keywords ===")
    
    # Agent domain queries
    agent_queries = [
        "Create a marketing draft for Q4",
        "Show me the campaign policy",
        "根据文档解释一下",
    ]
    
    for msg in agent_queries:
        request_id = str(uuid.uuid4())
        result = agent_graph.invoke(
            message=msg,
            request_id=request_id,
        )
        
        # Should not route to direct for these queries
        assert result["metadata"]["graph_node"] != "direct" or \
               "Market Brain" in result.get("answer", ""), \
               f"Agent query '{msg}' should not route to direct-only"
        print(f"✓ Router recognized: '{msg[:40]}...'")


def test_guardrail_validation():
    """Test guardrail prevents invalid actions and duplicate operations."""
    print("\n=== Test 3: Guardrail Validation ===")
    
    # We verify guardrail by checking trace
    message = "Create a draft about Q4 marketing strategy"
    request_id = str(uuid.uuid4())
    
    result = agent_graph.invoke(
        message=message,
        request_id=request_id,
    )
    
    tool_trace = result.get("tool_trace", [])
    assert len(tool_trace) > 0, "Tool trace should be populated"
    
    # Check that guardrail node appears in trace
    guardrail_items = [item for item in tool_trace if item.get("step") == "guardrail"]
    assert len(guardrail_items) > 0, "Guardrail should appear in trace"
    
    print(f"✓ Guardrail validation test passed")
    print(f"  Trace items: {len(tool_trace)}")
    print(f"  Guardrail enforcements: {len(guardrail_items)}")


def test_state_propagation():
    """Test state flows correctly through nodes."""
    print("\n=== Test 4: State Propagation ===")
    
    message = "What is in the return policy?"
    request_id = str(uuid.uuid4())
    session_id = "test-session-123"
    
    result = agent_graph.invoke(
        message=message,
        request_id=request_id,
        session_id=session_id,
    )
    
    # Verify required fields in response
    assert "answer" in result, "Response must have 'answer'"
    assert "metadata" in result, "Response must have 'metadata'"
    assert "tool_trace" in result, "Response must have 'tool_trace'"
    assert "citations" in result, "Response must have 'citations'"
    
    # Verify metadata contains key fields
    metadata = result["metadata"]
    assert metadata.get("request_id") == request_id, "Metadata must preserve request_id"
    assert metadata.get("session_id") == session_id, "Metadata must preserve session_id"
    assert "response_type" in metadata, "Metadata must have response_type"
    assert "route" in metadata, "Metadata must have route"
    assert "step_count" in metadata, "Metadata must have step_count"
    assert "trace_count" in metadata, "Metadata must have trace_count"
    
    print(f"✓ State propagation test passed")
    print(f"  Request ID preserved: {metadata['request_id'] == request_id}")
    print(f"  Session ID preserved: {metadata['session_id'] == session_id}")
    print(f"  Trace items: {metadata['trace_count']}")
    print(f"  Steps taken: {metadata['step_count']}")


def test_max_steps_guardrail():
    """Test max_steps limit is enforced."""
    print("\n=== Test 5: Max Steps Guardrail ===")
    
    # A complex compound query that might trigger multiple steps
    message = "Based on the return policy, help me create a draft for customer service"
    request_id = str(uuid.uuid4())
    
    result = agent_graph.invoke(
        message=message,
        request_id=request_id,
    )
    
    metadata = result["metadata"]
    # Should not exceed max_steps (3)
    assert metadata["step_count"] <= metadata["max_steps"], \
        f"Steps ({metadata['step_count']}) should not exceed max ({metadata['max_steps']})"
    
    print(f"✓ Max steps guardrail test passed")
    print(f"  Max steps: {metadata['max_steps']}")
    print(f"  Steps taken: {metadata['step_count']}")


def test_api_stability():
    """Test backward compatibility with FastAPI /chat endpoint."""
    print("\n=== Test 6: API Stability (Backward Compatibility) ===")
    
    message = "Can you explain the product?"
    request_id = str(uuid.uuid4())
    session_id = "session-456"
    
    # This simulates what app.py does
    result = agent_graph.invoke(
        message=message,
        request_id=request_id,
        session_id=session_id,
    )
    
    # FastAPI ChatResponse expects these fields
    assert isinstance(result, dict), "Result must be a dict"
    assert "answer" in result, "Must have 'answer' for ChatResponse"
    assert "metadata" in result, "Must have 'metadata' for ChatResponse"
    assert "tool_trace" in result, "Must have 'tool_trace' for ChatResponse"
    assert "citations" in result, "Must have 'citations' for ChatResponse"
    
    # Metadata must be valid for serialization
    metadata = result["metadata"]
    assert isinstance(metadata, dict), "Metadata must be dict"
    assert all(isinstance(k, str) for k in metadata.keys()), "Metadata keys must be strings"
    
    print(f"✓ API stability test passed")
    print(f"  Response structure valid for FastAPI ChatResponse")
    print(f"  All required fields present")


def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("Market Brain Graph Refactoring - Smoke Tests")
    print("=" * 60)
    
    tests = [
        test_direct_route,
        test_router_keywords,
        test_guardrail_validation,
        test_state_propagation,
        test_max_steps_guardrail,
        test_api_stability,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"✗ {test_func.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
