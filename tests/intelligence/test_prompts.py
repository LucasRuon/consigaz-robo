"""Testes de intelligence.prompts (load + render)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from intelligence.exceptions import (
    PromptMetadataError,
    PromptNameError,
    PromptNotFoundError,
    PromptRenderError,
    SchemaNotRegisteredError,
)
from intelligence.prompts import Prompt, load, render
from intelligence.schemas import register

FIXTURES = Path(__file__).parent / "fixtures" / "prompts"


def test_load_valid_returns_prompt() -> None:
    p = load("valid", prompts_dir=FIXTURES)
    assert isinstance(p, Prompt)
    assert p.name == "valid"
    assert p.version == "1.0.0"
    assert p.model == "gpt-4o-mini"
    assert p.temperature == 0.0
    assert p.response_schema is None
    assert "{nome}" in p.template
    assert "{observacao}" in p.template


def test_load_minimal_defaults() -> None:
    p = load("minimal", prompts_dir=FIXTURES)
    assert p.version == "0.1"
    assert p.model is None
    assert p.temperature is None
    assert p.response_schema is None


@pytest.mark.parametrize(
    "bad_name",
    [
        "/etc/passwd",
        "../escape",
        "sub/dir",
        "back\\slash",
        "",
    ],
)
def test_load_rejects_traversal(bad_name: str) -> None:
    with pytest.raises(PromptNameError):
        load(bad_name, prompts_dir=FIXTURES)


def test_load_missing_file_raises() -> None:
    with pytest.raises(PromptNotFoundError) as excinfo:
        load("inexistente", prompts_dir=FIXTURES)
    assert excinfo.value.name == "inexistente"
    assert "inexistente.md" in str(excinfo.value.path)


def test_load_no_frontmatter_raises() -> None:
    with pytest.raises(PromptMetadataError):
        load("no_frontmatter", prompts_dir=FIXTURES)


def test_load_malformed_yaml_raises() -> None:
    with pytest.raises(PromptMetadataError) as excinfo:
        load("malformed_yaml", prompts_dir=FIXTURES)
    assert excinfo.value.name == "malformed_yaml"
    assert excinfo.value.reason  # tem mensagem do parser


def test_load_missing_version_raises() -> None:
    with pytest.raises(PromptMetadataError) as excinfo:
        load("missing_version", prompts_dir=FIXTURES)
    assert "version" in excinfo.value.reason


@pytest.mark.usefixtures("clear_schema_registry")
def test_load_with_unknown_schema_fails_early() -> None:
    with pytest.raises(SchemaNotRegisteredError):
        load("with_unknown_schema", prompts_dir=FIXTURES)


@pytest.mark.usefixtures("clear_schema_registry")
def test_load_with_known_schema_succeeds() -> None:
    @register("TestClassification")
    class _T(BaseModel):
        decision: str

    p = load("with_known_schema", prompts_dir=FIXTURES)
    assert p.response_schema == "TestClassification"


def test_render_substitutes_placeholders() -> None:
    p = load("valid", prompts_dir=FIXTURES)
    out = render(p, {"nome": "Lucas", "observacao": "tudo certo"})
    assert "Lucas" in out
    assert "tudo certo" in out


def test_render_missing_placeholder_raises() -> None:
    p = load("valid", prompts_dir=FIXTURES)
    with pytest.raises(PromptRenderError) as excinfo:
        render(p, {"nome": "x"})
    assert "observacao" in excinfo.value.missing


def test_render_collects_all_missing_placeholders() -> None:
    p = load("valid", prompts_dir=FIXTURES)
    with pytest.raises(PromptRenderError) as excinfo:
        render(p, {})
    assert set(excinfo.value.missing) == {"nome", "observacao"}


def test_render_ignores_extra_params() -> None:
    p = load("valid", prompts_dir=FIXTURES)
    out = render(p, {"nome": "a", "observacao": "b", "extra": "ignorado"})
    assert "Lucas" not in out
    assert "ignorado" not in out


def test_render_no_placeholders_returns_template_as_is() -> None:
    p = load("minimal", prompts_dir=FIXTURES)
    out = render(p, {})
    assert "sem placeholders" in out


def test_default_prompts_dir_is_project_config() -> None:
    """Sanity: o default aponta para `<repo>/config/prompts/`."""
    from intelligence.prompts import _DEFAULT_PROMPTS_DIR

    assert _DEFAULT_PROMPTS_DIR.name == "prompts"
    assert _DEFAULT_PROMPTS_DIR.parent.name == "config"
