"""Testes do prompt `pilot-smoke` (load + render + erro de placeholder)."""

from __future__ import annotations

import pytest

import intelligence.schemas.pilot_smoke  # noqa: F401 — força registro de schemas
from intelligence.exceptions import PromptRenderError
from intelligence.prompts import load, render


def test_load_pilot_smoke_prompt() -> None:
    prompt = load("pilot-smoke")
    assert prompt.name == "pilot-smoke"
    assert prompt.version == "1"
    assert prompt.response_schema == "pilot-smoke-llm"
    assert prompt.temperature == 0.0


def test_render_pilot_smoke_prompt() -> None:
    prompt = load("pilot-smoke")
    rendered = render(prompt, {"operation": "2 + 3", "result": 5, "observation": "x"})
    assert "2 + 3" in rendered
    assert "Resultado obtido: 5" in rendered
    assert "Observação: x" in rendered


def test_render_missing_placeholder_raises() -> None:
    prompt = load("pilot-smoke")
    with pytest.raises(PromptRenderError):
        render(prompt, {"operation": "2 + 3"})
