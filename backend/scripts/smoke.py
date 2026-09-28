"""Stage 1 smoke test: one real call each to Gemini (chat + embeddings) and Tavily.

Usage (from backend/):  python scripts/smoke.py
Costs roughly 1 Tavily credit and a few hundred Gemini tokens.
"""

import sys
import time

from google import genai
from google.genai import types
from langchain_google_genai import ChatGoogleGenerativeAI
from tavily import TavilyClient

from app.config import get_settings


def check_model_names(client: genai.Client, chat_model: str, embed_model: str) -> None:
    available = {m.name.removeprefix("models/") for m in client.models.list()}
    for name in (chat_model, embed_model):
        status = "ok" if name in available else "NOT FOUND in models.list()"
        print(f"  model {name}: {status}")


def main() -> int:
    settings = get_settings()
    if missing := settings.missing_keys():
        print(f"Missing {', '.join(missing)}. Copy .env.example to .env and fill them in.")
        return 1

    print("Gemini")
    client = genai.Client(api_key=settings.gemini_api_key)
    check_model_names(client, settings.gemini_model, settings.gemini_embedding_model)

    llm = ChatGoogleGenerativeAI(model=settings.gemini_model, api_key=settings.gemini_api_key)
    start = time.perf_counter()
    reply = llm.invoke("Reply with exactly: citecheck ok")
    print(f"  chat ({(time.perf_counter() - start) * 1000:.0f} ms): {reply.text.strip()!r}")
    print(f"  usage: {reply.usage_metadata}")

    emb = client.models.embed_content(
        model=settings.gemini_embedding_model,
        contents="citation verification",
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    print(f"  embedding dims: {len(emb.embeddings[0].values)}")

    print("Tavily")
    tavily = TavilyClient(api_key=settings.tavily_api_key)
    start = time.perf_counter()
    result = tavily.search("What is LangGraph?", search_depth="basic", max_results=2)
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"  search ({elapsed_ms:.0f} ms): {len(result['results'])} results")
    for r in result["results"]:
        print(f"  - {r['title']} <{r['url']}>")

    print("\nSmoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
