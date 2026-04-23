from fastapi import FastAPI
from schemas import ChatRequest, ChatResponse
from core.config import APP_NAME
from orchestrator import Orchestrator
import uuid

app = FastAPI(title=APP_NAME)
orchestrator = Orchestrator()


@app.get("/")
def healthcheck():
    return {"status": "ok", "app": APP_NAME}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    request_id = str(uuid.uuid4())

    print({
        "event": "request_received",
        "request_id": request_id,
        "route": "/chat",
        "message": req.message,
        "session_id": req.session_id,
    })

    result = orchestrator.handle_chat(
        message=req.message,
        request_id=request_id,
        session_id=req.session_id
    )

    print({
        "event": "request_completed",
        "request_id": request_id,
        "route": "/chat",
        "metadata": result["metadata"],
    })

    return ChatResponse(**result)