import uuid

from fastapi import Depends, FastAPI

from agent_graph import agent_graph
from core.auth import require_api_key
from core.config import APP_NAME
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

    write_trace_log(
        {
            "event": "request_received",
            "request_id": request_id,
            "route": "/chat",
            "session_id": req.session_id,
            "message": req.message,
        }
    )

    result = agent_graph.invoke(
        message=req.message,
        request_id=request_id,
        session_id=req.session_id,
    )

    write_trace_log(
        {
            "event": "request_completed",
            "request_id": request_id,
            "route": "/chat",
            "metadata": result["metadata"],
        }
    )

    return ChatResponse(**result)


@app.post("/tools/{tool_name}", dependencies=[Depends(require_api_key)])
def execute_tool(tool_name: str, tool_input: dict):
    result = tool_registry.execute(tool_name, tool_input)

    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
    }
