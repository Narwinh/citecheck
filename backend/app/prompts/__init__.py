"""Prompt templates live as versioned .md files next to this module.

Placeholders use $name (string.Template), so literal braces in prompts are safe.
Bump the version suffix instead of editing a prompt that produced committed eval results.
"""

from pathlib import Path
from string import Template

PROMPTS_DIR = Path(__file__).parent


def render(name: str, **values: str) -> str:
    template = Template((PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8"))
    return template.substitute(**values)
