from pathlib import Path

import pytest

from app.config import load_settings, parse_env_file


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("GEMINI_API_KEY", "TAVILY_API_KEY", "GEMINI_MODEL", "GEMINI_EMBEDDING_MODEL"):
        monkeypatch.delenv(name, raising=False)


def test_parse_env_file_handles_comments_blanks_and_quotes(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text('# comment\n\nGEMINI_API_KEY="abc"\nTAVILY_API_KEY=xyz\nnot a pair\n')
    assert parse_env_file(env) == {"GEMINI_API_KEY": "abc", "TAVILY_API_KEY": "xyz"}


def test_missing_env_file_is_fine(tmp_path: Path):
    settings = load_settings(tmp_path / "does-not-exist")
    assert settings.missing_keys() == ["GEMINI_API_KEY", "TAVILY_API_KEY"]


def test_real_env_overrides_file(tmp_path: Path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GEMINI_MODEL=from-file\nGEMINI_API_KEY=file-key\n")
    monkeypatch.setenv("GEMINI_MODEL", "from-env")
    settings = load_settings(env)
    assert settings.gemini_model == "from-env"
    assert settings.gemini_api_key == "file-key"
    assert settings.missing_keys() == ["TAVILY_API_KEY"]
