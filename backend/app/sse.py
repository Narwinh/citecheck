"""Server-Sent Events framing.

Each event is `event: <name>` + `data: <json>` + a blank line. Comment lines
(starting with ':') are ignored by EventSource clients; we send one as a
heartbeat while a slow LLM call runs, so proxies (Hugging Face Spaces, Vercel)
don't close a connection that looks idle.
"""

import json
from typing import Any

HEARTBEAT = ": ping\n\n"


def format_event(event: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"
