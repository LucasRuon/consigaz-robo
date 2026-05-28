"""Excepthook que captura screenshot em exceções não tratadas."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

import pyautogui

from logger.setup import get_logger


def take_screenshot(path: Path) -> bool:
    """Captura screenshot em `path`. Retorna True em sucesso, False em qualquer falha."""
    log = get_logger(__name__)
    try:
        img = pyautogui.screenshot()
        img.save(str(path))
    except Exception as err:
        log.warning("screenshot_falhou", erro=str(err), tipo=type(err).__name__, path=str(path))
        return False
    return True


def install_excepthook(routine: str, errors_dir: Path = Path("logs/errors")) -> None:
    """Substitui `sys.excepthook` por wrapper que captura screenshot e re-delega."""
    errors_dir.mkdir(parents=True, exist_ok=True)
    previous = sys.excepthook
    log = get_logger(__name__)

    def hook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        log.error(
            "excecao_nao_tratada",
            tipo=exc_type.__name__,
            mensagem=str(exc_value),
        )
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        path = errors_dir / f"{timestamp}_{routine}.png"
        take_screenshot(path)
        previous(exc_type, exc_value, exc_tb)

    sys.excepthook = hook
