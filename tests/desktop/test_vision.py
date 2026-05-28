"""Testes unitários de wait_for_template com mocks de pyautogui e cv2."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from desktop.exceptions import TemplateNotFoundError


def _fake_screenshot() -> MagicMock:
    img = MagicMock()
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    img.__array__ = lambda self, dtype=None: arr
    return img


def _make_screen_array() -> np.ndarray:
    return np.zeros((100, 100, 3), dtype=np.uint8)


@pytest.fixture()
def template_file(tmp_path: Path) -> Path:
    """Cria arquivo de template PNG temporário."""
    p = tmp_path / "btn.png"
    import cv2
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    cv2.imwrite(str(p), img)
    return p


def test_match_imediato_retorna_coordenadas(template_file: Path) -> None:
    screen = np.zeros((100, 100, 3), dtype=np.uint8)
    pil_mock = MagicMock()
    pil_mock.__array__ = lambda self, dtype=None: screen

    with (
        patch("desktop.vision.pyautogui.screenshot", return_value=pil_mock),
        patch("desktop.vision.np.array", return_value=screen),
        patch("desktop.vision.cv2.cvtColor", return_value=screen),
        patch("desktop.vision.cv2.matchTemplate", return_value=np.array([[0.95]])),
        patch("desktop.vision.cv2.minMaxLoc", return_value=(0.0, 0.95, None, (20, 30))),
        patch("desktop.vision.cv2.imread", return_value=np.zeros((10, 10, 3), dtype=np.uint8)),
        patch.object(Path, "exists", return_value=True),
    ):
        from desktop.vision import wait_for_template
        x, y = wait_for_template(template_file, timeout=5.0, threshold=0.8)

    assert isinstance(x, int)
    assert isinstance(y, int)


def test_timeout_lanca_template_not_found(template_file: Path) -> None:
    screen = np.zeros((100, 100, 3), dtype=np.uint8)
    pil_mock = MagicMock()

    with (
        patch("desktop.vision.pyautogui.screenshot", return_value=pil_mock),
        patch("desktop.vision.np.array", return_value=screen),
        patch("desktop.vision.cv2.cvtColor", return_value=screen),
        patch("desktop.vision.cv2.matchTemplate", return_value=np.array([[0.3]])),
        patch("desktop.vision.cv2.minMaxLoc", return_value=(0.0, 0.3, None, (0, 0))),
        patch("desktop.vision.cv2.imread", return_value=np.zeros((10, 10, 3), dtype=np.uint8)),
        patch.object(Path, "exists", return_value=True),
        patch("desktop.vision.time.sleep"),
        patch("desktop.vision._ERRORS_DIR", Path("/tmp/test_errors")),
    ):
        from desktop.vision import wait_for_template
        with pytest.raises(TemplateNotFoundError) as exc_info:
            wait_for_template(template_file, timeout=0.01, threshold=0.8)

    err = exc_info.value
    assert err.template_path is not None
    assert err.elapsed >= 0


def test_arquivo_ausente_lanca_file_not_found(tmp_path: Path) -> None:
    caminho_inexistente = tmp_path / "nao_existe.png"
    with patch.object(Path, "exists", return_value=False):
        from desktop.vision import wait_for_template
        with pytest.raises(FileNotFoundError):
            wait_for_template(caminho_inexistente)


def test_threshold_default_e_0_8(template_file: Path) -> None:
    """Sem threshold explícito, deve usar 0.8 e retornar centro do match (loc + t_w//2, t_h//2)."""
    screen = np.zeros((100, 100, 3), dtype=np.uint8)
    pil_mock = MagicMock()
    # Template 10x10: centro = loc(5,5) + (5,5) = (10,10)
    template_10x10 = np.zeros((10, 10, 3), dtype=np.uint8)

    def minmax_spy(result: np.ndarray) -> tuple[float, float, None, tuple[int, int]]:
        return (0.0, 0.85, None, (5, 5))

    with (
        patch("desktop.vision.pyautogui.screenshot", return_value=pil_mock),
        patch("desktop.vision.np.array", return_value=screen),
        patch("desktop.vision.cv2.cvtColor", return_value=screen),
        patch("desktop.vision.cv2.matchTemplate", return_value=np.array([[0.85]])),
        patch("desktop.vision.cv2.minMaxLoc", side_effect=minmax_spy),
        patch("desktop.vision.cv2.imread", return_value=template_10x10),
        patch.object(Path, "exists", return_value=True),
    ):
        from desktop.vision import wait_for_template
        result = wait_for_template(template_file)  # sem threshold explícito

    # loc=(5,5), template 10x10 → centro = (5+5, 5+5) = (10, 10)
    assert result == (10, 10)


def test_fallback_path_usa_raiz_quando_plataforma_nao_existe(tmp_path: Path) -> None:
    template = tmp_path / "btn.png"
    import cv2 as cv
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    cv.imwrite(str(template), img)

    import sys
    plat = sys.platform
    platform_path = template.parent / plat / template.name

    assert not platform_path.exists()

    from desktop.vision import _resolve_template_path
    resolved = _resolve_template_path(template)
    assert resolved == template


def test_fallback_path_usa_plataforma_quando_existe(tmp_path: Path) -> None:
    import sys
    plat = sys.platform
    platform_dir = tmp_path / plat
    platform_dir.mkdir()
    template_root = tmp_path / "btn.png"
    template_plat = platform_dir / "btn.png"

    import cv2 as cv
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    cv.imwrite(str(template_root), img)
    cv.imwrite(str(template_plat), img)

    from desktop.vision import _resolve_template_path
    resolved = _resolve_template_path(template_root)
    assert resolved == template_plat


def test_poll_interval_chamado(template_file: Path) -> None:
    screen = np.zeros((100, 100, 3), dtype=np.uint8)
    pil_mock = MagicMock()
    sleep_calls: list[float] = []

    call_count = 0

    def fake_minmax(result: np.ndarray) -> tuple[float, float, None, tuple[int, int]]:
        nonlocal call_count
        call_count += 1
        score = 0.9 if call_count >= 2 else 0.1
        return (0.0, score, None, (10, 10))

    def fake_sleep(t: float) -> None:
        sleep_calls.append(t)

    with (
        patch("desktop.vision.pyautogui.screenshot", return_value=pil_mock),
        patch("desktop.vision.np.array", return_value=screen),
        patch("desktop.vision.cv2.cvtColor", return_value=screen),
        patch("desktop.vision.cv2.matchTemplate", return_value=np.array([[0.5]])),
        patch("desktop.vision.cv2.minMaxLoc", side_effect=fake_minmax),
        patch("desktop.vision.cv2.imread", return_value=np.zeros((10, 10, 3), dtype=np.uint8)),
        patch.object(Path, "exists", return_value=True),
        patch("desktop.vision.time.sleep", side_effect=fake_sleep),
    ):
        from desktop.vision import wait_for_template
        wait_for_template(template_file, timeout=5.0, poll_interval=0.5)

    assert len(sleep_calls) >= 1
    assert sleep_calls[0] == pytest.approx(0.5)
