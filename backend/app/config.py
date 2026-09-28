"""Settings loaded from environment variables, with an optional repo-root .env file.

Real environment variables always win over .env, so deployment secrets
(Hugging Face Spaces, Render) override anything local.
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE lines. Ignores blanks and # comments, strips matching quotes."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key.strip()] = value
    return values


class Settings(BaseModel):
    gemini_api_key: str = ""
    tavily_api_key: str = ""
    # Model names change often; override via env instead of editing code.
    gemini_model: str = "gemini-3.8-flash"
    # Comma-separated, tried in order when the model before fails (503 overload, or the
    # free tier's 20 requests/day/model quota). Empty string disables fallback.
    gemini_fallback_models: str = "gemini-3.7-flash,gemini-3.6-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    # 768 is a documented recommended size: 4x smaller than the 3072 default.
    embedding_dimensions: int = 768
    tavily_max_results: int = 5
    max_sub_queries: int = 4
    max_question_chars: int = 500
    # Gemini 3 thinking: minimal | low | medium | high. Measured per agent in the eval.
    # "minimal" is not accepted by every Gemini 3 model (gemini-3.7-flash rejects it with
    # a 400), which would break the fallback chain, so "low" is the floor.
    planner_thinking_level: str = "low"
    writer_thinking_level: str = "low"
    verifier_thinking_level: str = "low"
    reviser_thinking_level: str = "low"
    cache_dir: Path = Field(default=REPO_ROOT / "eval" / "cache")

    def missing_keys(self) -> list[str]:
        missing = []
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not self.tavily_api_key:
            missing.append("TAVILY_API_KEY")
        return missing


def load_settings(env_file: Path | None = DEFAULT_ENV_FILE) -> Settings:
    file_values = parse_env_file(env_file) if env_file else {}

    def get(name: str) -> str | None:
        return os.environ.get(name) or file_values.get(name) or None

    overrides = {
        field: value for field in Settings.model_fields if (value := get(field.upper())) is not None
    }
    return Settings(**overrides)


@lru_cache
def get_settings() -> Settings:
    return load_settings()
