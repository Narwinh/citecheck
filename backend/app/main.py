"""FastAPI app: health, examples, and the streaming /api/ask endpoint.

The LangGraph pipeline is synchronous, so it runs in a worker thread that
pushes events onto an asyncio queue. The response generator drains the queue
as SSE, sending a heartbeat comment whenever nothing arrives for a while, and
stops early if the client disconnects.

Run locally:  uvicorn app.main:app --reload --port 8000   (from backend/)
"""

import asyncio
import json
import logging
import threading
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from google.genai import errors as genai_errors
from pydantic import BaseModel, Field, field_validator

from app.agents.llm import AllModelsFailed
from app.config import Settings, get_settings
from app.graph import build_graph, stream_events
from app.ratelimit import RateLimiter, client_ip
from app.sse import HEARTBEAT, format_event

log = logging.getLogger("citecheck")
EXAMPLES_PATH = Path(__file__).parent / "examples.json"
HEARTBEAT_S = 15.0

GraphFactory = Callable[[str | None], Any]


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    mode: Literal["strict", "lenient"] = "strict"

    @field_validator("question")
    @classmethod
    def strip(cls, value: str) -> str:
        return " ".join(value.split())


def error_payload(exc: BaseException) -> dict[str, str]:
    if isinstance(exc, AllModelsFailed) and exc.daily_quota_exhausted:
        return {
            "code": "quota",
            "message": "The research engine has used today's free model quota. "
            "Try again later, or add your own Gemini API key.",
        }
    if isinstance(exc, AllModelsFailed) or is_rate_limited(exc):
        return {
            "code": "unavailable",
            "message": "The model service is busy or rate-limited right now. "
            "Please try again in a minute.",
        }
    return {"code": "internal", "message": "Something went wrong while researching this question."}


def is_rate_limited(exc: BaseException) -> bool:
    """A 429/503 from any Google API call outside the model chain (e.g. embeddings)."""
    return isinstance(exc, genai_errors.APIError) and exc.code in (429, 503)


def default_graph_factory(settings: Settings) -> GraphFactory:
    from app.services.factory import make_agents

    shared: dict[str, Any] = {}

    def factory(api_key: str | None) -> Any:
        if api_key:  # the visitor's own key: build a private graph, never cache or log it
            return build_graph(make_agents(settings.model_copy(update={"gemini_api_key": api_key})))
        if "graph" not in shared:
            shared["graph"] = build_graph(make_agents(settings))
        return shared["graph"]

    return factory


async def event_stream(
    request: Request, graph: Any, question: str, mode: str
) -> AsyncIterator[str]:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

    def put(kind: str, item: Any) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, (kind, item))

    def worker() -> None:
        try:
            for chunk in stream_events(graph, question, mode=mode):
                put("event", chunk)
        except Exception as exc:  # noqa: BLE001 - surfaced to the client as an error event
            log.exception("pipeline failed")
            put("error", exc)
        finally:
            put("end", None)

    threading.Thread(target=worker, daemon=True, name="citecheck-pipeline").start()
    while True:
        try:
            kind, item = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_S)
        except TimeoutError:
            if await request.is_disconnected():
                return  # the worker finishes its current step and exits on its own
            yield HEARTBEAT
            continue
        if kind == "end":
            return
        if kind == "event":
            yield format_event(item["event"], item["data"])
        else:
            yield format_event("error", error_payload(item))


def create_app(settings: Settings | None = None, graph_factory: GraphFactory | None = None):
    settings = settings or get_settings()
    graph_factory = graph_factory or default_graph_factory(settings)
    limiter = RateLimiter(settings.rate_limit_per_hour, 3600)
    examples = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))

    app = FastAPI(title="CiteCheck API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Gemini-Key"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/examples")
    def get_examples() -> list[dict[str, str]]:
        return examples

    @app.post("/api/ask")
    async def ask(
        body: AskRequest,
        request: Request,
        x_gemini_key: str | None = Header(default=None),
    ):
        if len(body.question) > settings.max_question_chars:
            return JSONResponse(
                {"detail": f"Questions are limited to {settings.max_question_chars} characters."},
                status_code=422,
            )
        own_key = (x_gemini_key or "").strip() or None
        if own_key is None:
            retry_after = limiter.check(client_ip(request, settings.trusted_proxies))
            if retry_after is not None:
                return JSONResponse(
                    {
                        "detail": f"Rate limit: {settings.rate_limit_per_hour} questions per hour. "
                        "Add your own Gemini key to skip it.",
                        "retry_after_s": retry_after,
                    },
                    status_code=429,
                    headers={"Retry-After": str(int(retry_after) + 1)},
                )
        graph = graph_factory(own_key)
        return StreamingResponse(
            event_stream(request, graph, body.question, body.mode),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()
