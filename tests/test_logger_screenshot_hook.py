"""Testes para `logger.screenshot_hook` (excepthook + captura de tela)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import TracebackType
from typing import Any

import pytest
import structlog

from logger.screenshot_hook import install_excepthook, take_screenshot
from logger.setup import setup_logging


class _FakeScreenshot:
    """Substitui `pyautogui.screenshot`. Salva PNG vazio ou levanta exceção."""

    def __init__(self, raises: BaseException | None = None) -> None:
        self.raises = raises
        self.called_with: Path | None = None

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self.raises is not None:
            raise self.raises

        class _Img:
            def __init__(self, called_with_setter: _FakeScreenshot) -> None:
                self._setter = called_with_setter

            def save(self_inner, path: str | Path) -> None:
                Path(path).write_bytes(b"PNGFAKE")
                self_inner._setter.called_with = Path(path)

        return _Img(self)


@pytest.fixture
def reset_logging() -> None:
    yield
    root = logging.getLogger()
    for handler in list(root.handlers):
        handler.close()
        root.removeHandler(handler)
    structlog.reset_defaults()


@pytest.fixture
def restore_excepthook() -> None:
    original = sys.excepthook
    yield
    sys.excepthook = original


def test_take_screenshot_sucesso_retorna_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeScreenshot()
    monkeypatch.setattr("pyautogui.screenshot", fake)

    path = tmp_path / "ok.png"
    assert take_screenshot(path) is True
    assert path.exists()
    assert fake.called_with == path


def test_take_screenshot_falha_retorna_false_sem_propagar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeScreenshot(raises=RuntimeError("sem permissão"))
    monkeypatch.setattr("pyautogui.screenshot", fake)

    path = tmp_path / "fail.png"
    # NÃO propaga
    assert take_screenshot(path) is False
    assert not path.exists()


def test_install_excepthook_captura_screenshot_em_excecao(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    restore_excepthook: None,
    reset_logging: None,
) -> None:
    errors_dir = tmp_path / "errors"
    setup_logging("rotina_x", log_dir=tmp_path, level="INFO")

    fake = _FakeScreenshot()
    monkeypatch.setattr("pyautogui.screenshot", fake)

    install_excepthook("rotina_x", errors_dir=errors_dir)

    # simula uma exceção não tratada
    try:
        raise ValueError("erro_proposital")
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()
    assert exc_type is ValueError

    # invoca o hook diretamente (não dá pra simular uncaught exception em pytest)
    sys.excepthook(exc_type, exc_value, exc_tb)

    pngs = list(errors_dir.glob("*_rotina_x.png"))
    assert len(pngs) == 1
    assert pngs[0].read_bytes() == b"PNGFAKE"


def test_install_excepthook_cria_errors_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    restore_excepthook: None,
    reset_logging: None,
) -> None:
    errors_dir = tmp_path / "nested" / "errors"
    setup_logging("r", log_dir=tmp_path, level="INFO")
    monkeypatch.setattr("pyautogui.screenshot", _FakeScreenshot())

    assert not errors_dir.exists()
    install_excepthook("r", errors_dir=errors_dir)
    assert errors_dir.is_dir()


def test_excepthook_re_raise_chama_previous_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    restore_excepthook: None,
    reset_logging: None,
) -> None:
    """O hook anterior deve ser chamado depois da captura, com os mesmos argumentos."""
    setup_logging("prev", log_dir=tmp_path, level="INFO")
    monkeypatch.setattr("pyautogui.screenshot", _FakeScreenshot())

    captured: list[tuple[type[BaseException], BaseException, TracebackType | None]] = []

    def previous_hook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        captured.append((exc_type, exc_value, exc_tb))

    sys.excepthook = previous_hook
    install_excepthook("prev", errors_dir=tmp_path / "errors")

    try:
        raise RuntimeError("delegar")
    except RuntimeError:
        exc_type, exc_value, exc_tb = sys.exc_info()
    sys.excepthook(exc_type, exc_value, exc_tb)

    assert len(captured) == 1
    assert captured[0][0] is RuntimeError
    assert str(captured[0][1]) == "delegar"


def test_screenshot_falha_nao_mascara_excecao_original(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    restore_excepthook: None,
    reset_logging: None,
) -> None:
    """Se a captura falhar, a exceção original ainda deve chegar ao previous hook."""
    setup_logging("mask", log_dir=tmp_path, level="INFO")
    monkeypatch.setattr(
        "pyautogui.screenshot", _FakeScreenshot(raises=RuntimeError("sem perm"))
    )

    captured: list[type[BaseException]] = []

    def previous_hook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        captured.append(exc_type)

    sys.excepthook = previous_hook
    install_excepthook("mask", errors_dir=tmp_path / "errors")

    try:
        raise ValueError("original")
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()
    sys.excepthook(exc_type, exc_value, exc_tb)

    # exceção original chegou — captura falhou silenciosa
    assert captured == [ValueError]
