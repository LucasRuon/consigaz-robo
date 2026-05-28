"""Ancoragem visual via OpenCV: wait_for_template com polling e fallback de path por SO."""

from __future__ import annotations

import contextlib
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import pyautogui

from desktop.exceptions import TemplateNotFoundError
from logger.setup import get_logger

_ERRORS_DIR = Path("logs/errors")


def _resolve_template_path(path: str | Path) -> Path:
    """Busca assets/templates/{sys.platform}/<name>; fallback assets/templates/<name>."""
    p = Path(path)
    platform_specific = p.parent / sys.platform / p.name
    if platform_specific.exists():
        return platform_specific
    return p


def wait_for_template(
    path: str | Path,
    timeout: float = 15.0,
    threshold: float = 0.8,
    poll_interval: float = 0.5,
) -> tuple[int, int]:
    """Aguarda template aparecer na tela via template matching.

    Retorna (x, y) do centro do match. Lança TemplateNotFoundError após timeout.
    """
    log = get_logger(__name__)
    resolved = _resolve_template_path(path)

    if not resolved.exists():
        raise FileNotFoundError(f"Template não encontrado em disco: {resolved}")

    template_img = cv2.imread(str(resolved))
    if template_img is None:
        raise FileNotFoundError(f"Não foi possível carregar imagem: {resolved}")

    t_h, t_w = template_img.shape[:2]
    deadline = time.monotonic() + timeout
    start = time.monotonic()

    while time.monotonic() < deadline:
        screenshot = pyautogui.screenshot()
        screen_np = np.array(screenshot)
        screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

        result = cv2.matchTemplate(screen_bgr, template_img, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            cx = max_loc[0] + t_w // 2
            cy = max_loc[1] + t_h // 2
            log.debug("template_encontrado", path=str(resolved), score=round(max_val, 3))
            return cx, cy

        time.sleep(poll_interval)

    elapsed = time.monotonic() - start
    _ERRORS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    screenshot_path = _ERRORS_DIR / f"{timestamp}_template_timeout.png"

    with contextlib.suppress(Exception):
        pyautogui.screenshot().save(str(screenshot_path))

    raise TemplateNotFoundError(str(resolved), str(screenshot_path), elapsed)
