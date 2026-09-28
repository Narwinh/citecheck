"""Build the real (API-backed, disk-cached) services from settings."""

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import Settings
from app.services.embeddings import CachedEmbedder, gemini_embed_fn
from app.services.search import CachedSearch


def make_llm(settings: Settings, thinking_level: str) -> list[ChatGoogleGenerativeAI]:
    """Primary model first, then the fallback used when the primary errors (e.g. 503 overload).

    Temperature is left unset: for Gemini 3 the integration defaults it to 1.0,
    and the docs warn lower values can cause loops and weaker reasoning.
    """
    models = [settings.gemini_model]
    if settings.gemini_fallback_model and settings.gemini_fallback_model != settings.gemini_model:
        models.append(settings.gemini_fallback_model)
    return [
        ChatGoogleGenerativeAI(
            model=name,
            api_key=settings.gemini_api_key,
            thinking_level=thinking_level,
            # Few retries on the primary so an overloaded model hands off quickly.
            max_retries=2 if i == 0 and len(models) > 1 else 6,
        )
        for i, name in enumerate(models)
    ]


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
