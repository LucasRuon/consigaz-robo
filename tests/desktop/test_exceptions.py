"""Testes unitários das exceções customizadas do módulo Desktop."""

from __future__ import annotations

import pytest

from desktop.exceptions import (
    InteractionError,
    PlatformError,
    TemplateNotFoundError,
    UnsupportedPlatformError,
)


def test_platform_error_is_runtime_error() -> None:
    assert issubclass(PlatformError, RuntimeError)


def test_template_not_found_error_is_runtime_error() -> None:
    assert issubclass(TemplateNotFoundError, RuntimeError)


def test_interaction_error_is_runtime_error() -> None:
    assert issubclass(InteractionError, RuntimeError)


def test_unsupported_platform_error_is_runtime_error() -> None:
    assert issubclass(UnsupportedPlatformError, RuntimeError)


def test_template_not_found_error_atributos() -> None:
    err = TemplateNotFoundError("btn.png", "logs/errors/err.png", 15.3)
    assert err.template_path == "btn.png"
    assert err.screenshot_path == "logs/errors/err.png"
    assert err.elapsed == pytest.approx(15.3)


def test_template_not_found_error_mensagem() -> None:
    err = TemplateNotFoundError("btn.png", "logs/err.png", 5.0)
    assert "btn.png" in str(err)
    assert "5.0" in str(err)


def test_interaction_error_atributos_completos() -> None:
    err = InteractionError("click", "assets/templates/btn.png")
    assert err.action == "click"
    assert err.template_path == "assets/templates/btn.png"


def test_interaction_error_sem_template() -> None:
    err = InteractionError("type_text")
    assert err.action == "type_text"
    assert err.template_path is None


def test_interaction_error_mensagem() -> None:
    err = InteractionError("click", "btn.png")
    assert "click" in str(err)
    assert "btn.png" in str(err)
