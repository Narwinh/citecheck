import json

from fastapi.testclient import TestClient

from app.agents.llm import AllModelsFailed
from app.agents.reviser import ReviserOutput, RevisionOut
from app.config import Settings
from app.graph import build_graph
from app.main import create_app
from app.ratelimit import RateLimiter
from tests.test_graph import FIRST_PASS, agents


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = [line for line in block.splitlines() if not line.startswith(":")]
        if not lines:
            continue
        name = lines[0].removeprefix("event: ")
        events.append((name, json.loads(lines[1].removeprefix("data: "))))
    return events


def client(tmp_path, graph_factory=None, **settings):
    def default_factory(api_key):
        return build_graph(
            agents(
                tmp_path,
                verifier_outputs=[FIRST_PASS],
                reviser_outputs=[
                    ReviserOutput(decisions=[RevisionOut(claim_id=2, action="remove")])
                ],
            )
        )

    s = Settings(gemini_api_key="k", tavily_api_key="k", **settings)
    return TestClient(create_app(s, graph_factory or default_factory))


def test_health_and_examples(tmp_path):
    c = client(tmp_path)
    assert c.get("/api/health").json() == {"status": "ok"}
    assert len(c.get("/api/examples").json()) >= 4


def test_ask_streams_every_event_type_in_order(tmp_path):
    r = client(tmp_path).post("/api/ask", json={"question": "How tall is the Eiffel Tower?"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    names = [name for name, _ in parse_sse(r.text)]
    order = ["subqueries", "sources", "draft", "verdict", "revision", "final"]
    first_seen = [n for n in dict.fromkeys(names) if n in order]
    assert first_seen == order
    assert names[0] == "stage" and names[-1] == "final"


def test_rate_limit_returns_429_but_own_key_skips_it(tmp_path):
    c = client(tmp_path, rate_limit_per_hour=2)
    body = {"question": "How tall is the Eiffel Tower?"}
    assert c.post("/api/ask", json=body).status_code == 200
    assert c.post("/api/ask", json=body).status_code == 200
    limited = c.post("/api/ask", json=body)
    assert limited.status_code == 429
    assert "Retry-After" in limited.headers
    assert c.post("/api/ask", json=body, headers={"X-Gemini-Key": "mine"}).status_code == 200


def test_own_key_is_passed_to_the_graph_factory(tmp_path):
    seen = []

    def factory(api_key):
        seen.append(api_key)
        return build_graph(agents(tmp_path, verifier_outputs=[FIRST_PASS], reviser_outputs=[
            ReviserOutput(decisions=[RevisionOut(claim_id=2, action="remove")])]))  # fmt: skip

    c = client(tmp_path, graph_factory=factory)
    c.post("/api/ask", json={"question": "abc?"}, headers={"X-Gemini-Key": "  mine  "})
    c.post("/api/ask", json={"question": "abc?"})
    assert seen == ["mine", None]


def test_validation_rejects_bad_input(tmp_path):
    c = client(tmp_path, max_question_chars=20)
    assert c.post("/api/ask", json={"question": "hi"}).status_code == 422
    assert c.post("/api/ask", json={"question": "x" * 30}).status_code == 422
    assert (
        c.post("/api/ask", json={"question": "fine question", "mode": "loose"}).status_code == 422
    )


def test_pipeline_failure_becomes_an_error_event(tmp_path):
    class QuotaGraph:
        def stream(self, *args, **kwargs):
            raise AllModelsFailed([RuntimeError("429 RESOURCE_EXHAUSTED PerDay")])
            yield  # pragma: no cover

    c = client(tmp_path, graph_factory=lambda key: QuotaGraph())
    events = parse_sse(c.post("/api/ask", json={"question": "abc?"}).text)
    assert events == [("error", events[0][1])]
    assert events[0][1]["code"] == "quota"


def test_embedding_rate_limit_maps_to_unavailable():
    from google.genai import errors

    from app.main import error_payload

    exc = errors.ClientError(429, {"error": {"message": "quota"}})
    assert error_payload(exc)["code"] == "unavailable"
    assert error_payload(ValueError("boom"))["code"] == "internal"


def test_rate_limiter_window_slides():
    now = [0.0]
    rl = RateLimiter(limit=2, window_s=10, clock=lambda: now[0])
    assert rl.check("ip") is None and rl.check("ip") is None
    assert rl.check("ip") == 10.0
    assert rl.check("other") is None
    now[0] = 10.0
    assert rl.check("ip") is None


def test_client_ip_ignores_spoofed_forwarded_entries():
    from starlette.requests import Request

    from app.ratelimit import client_ip

    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"6.6.6.6, 1.2.3.4")],
        "client": ("10.0.0.1", 1),
    }
    request = Request(scope)
    assert client_ip(request, trusted_proxies=1) == "1.2.3.4"
    assert client_ip(request, trusted_proxies=0) == "10.0.0.1"
