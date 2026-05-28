"""Load + render de prompts versionados em arquivos `.md` com frontmatter YAML."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from intelligence.exceptions import (
    PromptMetadataError,
    PromptNameError,
    PromptNotFoundError,
    PromptRenderError,
)
from intelligence.schemas import get_schema

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_PROMPTS_DIR = _PROJECT_ROOT / "config" / "prompts"


@dataclass(frozen=True)
class Prompt:
    """Prompt carregado de `.md` com metadados do frontmatter."""

    name: str
    template: str
    version: str
    model: str | None
    temperature: float | None
    response_schema: str | None


class _Placeholders(dict[str, Any]):
    """Dict que registra chaves ausentes em `str.format_map` em vez de KeyError."""

    def __init__(self, params: dict[str, Any]) -> None:
        super().__init__(params)
        self.missing: list[str] = []

    def __missing__(self, key: str) -> str:
        self.missing.append(key)
        return "{" + key + "}"


def _validate_name(name: str) -> None:
    if not name or "/" in name or "\\" in name or ".." in name:
        raise PromptNameError(name=name)


def load(name: str, prompts_dir: Path | None = None) -> Prompt:
    """Carrega `<prompts_dir>/<name>.md`, parseia frontmatter e valida metadata.

    Lança:
        PromptNameError, PromptNotFoundError, PromptMetadataError,
        SchemaNotRegisteredError (se `response_schema` referencia nome ausente)
    """
    _validate_name(name)
    base = prompts_dir or _DEFAULT_PROMPTS_DIR
    path = base / f"{name}.md"
    if not path.exists():
        raise PromptNotFoundError(name=name, path=path)

    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise PromptMetadataError(
            name=name, reason="frontmatter ausente ou malformado"
        )

    try:
        raw_meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        raise PromptMetadataError(name=name, reason=str(e)) from e

    meta: dict[str, Any] = raw_meta or {}
    if not isinstance(meta, dict):
        raise PromptMetadataError(
            name=name, reason="frontmatter deve ser mapping YAML"
        )
    if "version" not in meta:
        raise PromptMetadataError(name=name, reason="campo 'version' obrigatório")

    response_schema = meta.get("response_schema")
    if response_schema is not None:
        get_schema(response_schema)  # valida cedo

    return Prompt(
        name=name,
        template=match.group(2),
        version=str(meta["version"]),
        model=meta.get("model"),
        temperature=meta.get("temperature"),
        response_schema=response_schema,
    )


def render(prompt: Prompt, params: dict[str, Any]) -> str:
    """Substitui placeholders `{var}` no template do prompt.

    Chave extra em `params` é ignorada (permite reuso de dict).
    Placeholder ausente → `PromptRenderError(missing=[...])`.
    """
    holder = _Placeholders(params)
    rendered = prompt.template.format_map(holder)
    if holder.missing:
        raise PromptRenderError(name=prompt.name, missing=holder.missing)
    return rendered
