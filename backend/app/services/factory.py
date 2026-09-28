"""Build the real (API-backed, disk-cached) services from settings."""

from app.config import Settings
from app.services.embeddings import CachedEmbedder, gemini_embed_fn
from app.services.search import CachedSearch


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
