from time import perf_counter
from typing import AsyncIterator, Union
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.config import settings
from core.logging import log_event
from schemas import ChatMetadata, ChatRequest, ChatResponse
from services.llm_service import LLMService


router = APIRouter(tags=["chat"])
llm_service = LLMService(model_name=settings.model_name)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> Union[ChatResponse, StreamingResponse]:
    request_id = str(uuid4())
    route = "/chat"
    started_at = perf_counter()

    log_event(
        "chat.request.received",
        request_id=request_id,
        route=route,
        model=settings.model_name,
        session_id=request.session_id,
        stream=request.stream,
    )

    if request.stream:
        async def token_stream() -> AsyncIterator[str]:
            async for chunk in llm_service.stream_response(request.message):
                yield chunk

            latency_ms = int((perf_counter() - started_at) * 1000)
            log_event(
                "chat.response.completed",
                request_id=request_id,
                route=route,
                latency_ms=latency_ms,
                model=settings.model_name,
                session_id=request.session_id,
                stream=True,
            )

        return StreamingResponse(token_stream(), media_type="text/plain")

    answer = await llm_service.generate_response(request.message)
    latency_ms = int((perf_counter() - started_at) * 1000)

    log_event(
        "chat.response.completed",
        request_id=request_id,
        route=route,
        latency_ms=latency_ms,
        model=settings.model_name,
        session_id=request.session_id,
        stream=False,
    )

    return ChatResponse(
        answer=answer,
        metadata=ChatMetadata(
            request_id=request_id,
            model=settings.model_name,
            latency_ms=latency_ms,
            session_id=request.session_id,
            route=route,
        ),
    )
