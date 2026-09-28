"""Build the real (API-backed, disk-cached) services from settings."""

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import Settings
from app.services.embeddings import CachedEmbedder, gemini_embed_fn
from app.services.search import CachedSearch


def make_llm(settings: Settings, thinking_level: str) -> ChatGoogleGenerativeAI:
    # Temperature is left unset: for Gemini 3 the integration defaults it to 1.0,
    # and the docs warn lower values can cause loops and weaker reasoning.
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=settings.gemini_api_key,
        thinking_level=thinking_level,
        max_retries=6,  # built-in exponential backoff, including 429s
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
