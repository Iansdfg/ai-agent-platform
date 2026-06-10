import uuid
from typing import Any, Dict, List

from fastapi import Depends, FastAPI

from agent_graph import agent_graph
from core.auth import require_api_key
from core.config import APP_NAME
from core.logging import log_event
from core.tracing import write_trace_log
from db import init_db
from schemas import ChatRequest, ChatResponse
from tools.registry import build_default_registry


app = FastAPI(title=APP_NAME)
tool_registry = build_default_registry()


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def healthcheck():
    return {"status": "ok", "app": APP_NAME}


@app.get("/tools", dependencies=[Depends(require_api_key)])
def list_tools():
    return {"tools": tool_registry.list_tools()}


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
def chat(req: ChatRequest):
    request_id = str(uuid.uuid4())
    message_chars = len(req.message or "")

    write_trace_log(
        {
            "event": "request_received",
            "request_id": request_id,
            "route": "/chat",
            "session_id": req.session_id,
            "message": req.message,
        }
    )

    log_event(
        "eval_process_request_started",
        request_id=request_id,
        route="/chat",
        session_id=req.session_id,
        message_chars=message_chars,
    )

    try:
        result = agent_graph.invoke(
            message=req.message,
            request_id=request_id,
            session_id=req.session_id,
        )
    except Exception as exc:
        log_event(
            "eval_process_request_failed",
            request_id=request_id,
            route="/chat",
            session_id=req.session_id,
            error=str(exc),
        )
        raise

    public_result = _to_public_chat_result(result)

    write_trace_log(
        {
            "event": "request_completed",
            "request_id": request_id,
            "route": "/chat",
            "metadata": public_result["metadata"],
        }
    )

    log_event(
        "eval_process_request_completed",
        request_id=request_id,
        route="/chat",
        session_id=req.session_id,
        latency_ms=public_result["metadata"].get("latency_ms"),
        graph_node=public_result["metadata"].get("graph_node"),
        step_count=public_result["metadata"].get("step_count"),
        trace_count=public_result["metadata"].get("trace_count"),
        retrieved_chunk_count=public_result["metadata"].get("retrieved_chunk_count"),
        has_tool_result=public_result["metadata"].get("has_tool_result"),
    )

    return ChatResponse(**public_result)


@app.post("/tools/{tool_name}", dependencies=[Depends(require_api_key)])
def execute_tool(tool_name: str, tool_input: dict):
    result = tool_registry.execute(tool_name, tool_input)

    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
    }


def _to_public_chat_result(result: Dict[str, Any]) -> Dict[str, Any]:
    metadata = dict(result.get("metadata", {}))
    detailed_trace = result.get("tool_trace", [])
    detailed_citations = result.get("citations", [])

    tool_trace = _trace_names(detailed_trace)
    citations = _citation_sources(detailed_citations)

    metadata.setdefault("token_usage", {"input": 0, "output": 0})
    metadata.setdefault("tool_trace_details", detailed_trace)
    metadata.setdefault("citation_details", detailed_citations)
    metadata.setdefault("citation_sources", citations)

    return {
        "answer": result.get("answer", ""),
        "metadata": metadata,
        "tool_trace": tool_trace,
        "citations": citations,
    }


def _trace_names(trace_items: List[Any]) -> List[str]:
    names = []
    for item in trace_items:
        if isinstance(item, str):
            name = item
        elif isinstance(item, dict):
            name = item.get("name") or item.get("step")
        else:
            name = str(item)
        if name:
            names.append(str(name))
    return names


def _citation_sources(citations: List[Any]) -> List[str]:
    sources = []
    for citation in citations:
        if isinstance(citation, str):
            source = citation
        elif isinstance(citation, dict):
            source = citation.get("source") or citation.get("doc_id")
        else:
            source = str(citation)
        if source and source not in sources:
            sources.append(str(source))
    return sources
