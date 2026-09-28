"""Build the real (API-backed, disk-cached) services from settings."""

from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.planner import structured_planner
from app.agents.retriever import RetrieverConfig
from app.agents.reviser import structured_reviser
from app.agents.verifier import structured_verifier
from app.agents.writer import structured_writer
from app.config import Settings
from app.graph import Agents
from app.services.embeddings import CachedEmbedder, gemini_embed_fn
from app.services.search import CachedSearch


def make_llm(settings: Settings, thinking_level: str) -> list[ChatGoogleGenerativeAI]:
    """Primary model first, then the fallback used when the primary errors (e.g. 503 overload).

    Temperature is left unset: for Gemini 3 the integration defaults it to 1.0,
    and the docs warn lower values can cause loops and weaker reasoning.
    """
    fallbacks = [m.strip() for m in settings.gemini_fallback_models.split(",") if m.strip()]
    models = list(dict.fromkeys([settings.gemini_model, *fallbacks]))
    return [
        ChatGoogleGenerativeAI(
            model=name,
            api_key=settings.gemini_api_key,
            thinking_level=thinking_level,
            # No retries while another model is next in line: a 429 for an exhausted
            # daily quota won't clear by retrying, so hand off immediately.
            max_retries=1 if i < len(models) - 1 else 3,
        )
        for i, name in enumerate(models)
    ]


def make_judge_llm(settings: Settings) -> list[ChatGoogleGenerativeAI]:
    names = [m.strip() for m in settings.judge_models.split(",") if m.strip()]
    return [
        ChatGoogleGenerativeAI(
            model=name,
            api_key=settings.gemini_api_key,
            max_retries=1 if i < len(names) - 1 else 3,
        )
        for i, name in enumerate(names)
    ]


def make_agents(settings: Settings, top_k: int = 10) -> Agents:
    return Agents(
        search=make_search(settings),
        embedder=make_embedder(settings),
        planner=structured_planner(make_llm(settings, settings.planner_thinking_level)),
        writer=structured_writer(make_llm(settings, settings.writer_thinking_level)),
        verifier=structured_verifier(make_llm(settings, settings.verifier_thinking_level)),
        reviser=structured_reviser(make_llm(settings, settings.reviser_thinking_level)),
        retriever_cfg=RetrieverConfig(top_k=top_k),
        max_sub_queries=settings.max_sub_queries,
    )


def make_search(settings: Settings) -> CachedSearch:
    return CachedSearch.from_api_key(
        settings.tavily_api_key,
        settings.cache_dir / "tavily",
        max_results=settings.tavily_max_results,
    )


def make_embedder(settings: Settings) -> CachedEmbedder:
    model, dims = settings.gemini_embedding_model, settings.embedding_dimensions
    return CachedEmbedder(
        gemini_embed_fn(settings.gemini_api_key, model, dims),
        settings.cache_dir / "embeddings.sqlite",
        cache_namespace=f"{model}:{dims}",
    )
