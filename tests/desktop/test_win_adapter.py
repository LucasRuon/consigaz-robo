"""Testes unitários do WindowsAdapter com mock de pygetwindow e pyautogui."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from desktop.exceptions import PlatformError
from desktop.platform.win import WindowsAdapter


@pytest.fixture()
def adapter() -> WindowsAdapter:
    return WindowsAdapter()


def test_launch_app_chama_popen(adapter: WindowsAdapter) -> None:
    with patch("desktop.platform.win.subprocess.Popen") as mock_popen:
        adapter.launch_app("app.exe")
    mock_popen.assert_called_once_with(["app.exe"])


def test_launch_app_executavel_ausente_lanca_platform_error(adapter: WindowsAdapter) -> None:
    with patch("desktop.platform.win.subprocess.Popen", side_effect=FileNotFoundError):
        with pytest.raises(PlatformError, match="app.exe"):
            adapter.launch_app("app.exe")


def test_focus_window_chama_activate(adapter: WindowsAdapter) -> None:
    mock_win = MagicMock()
    mock_gw = MagicMock()
    mock_gw.getWindowsWithTitle.return_value = [mock_win]

    with patch.dict("sys.modules", {"pygetwindow": mock_gw}):
        adapter.focus_window("MeuApp")

    mock_win.activate.assert_called_once()


def test_focus_window_sem_janela_lanca_platform_error(adapter: WindowsAdapter) -> None:
    mock_gw = MagicMock()
    mock_gw.getWindowsWithTitle.return_value = []

    with patch.dict("sys.modules", {"pygetwindow": mock_gw}):
        with pytest.raises(PlatformError, match="MeuApp"):
            adapter.focus_window("MeuApp")


def test_focus_window_activate_falha_lanca_platform_error(adapter: WindowsAdapter) -> None:
    mock_win = MagicMock()
    mock_win.activate.side_effect = Exception("janela travada")
    mock_gw = MagicMock()
    mock_gw.getWindowsWithTitle.return_value = [mock_win]

    with patch.dict("sys.modules", {"pygetwindow": mock_gw}):
        with pytest.raises(PlatformError):
            adapter.focus_window("MeuApp")


def test_modifier_key_retorna_ctrl(adapter: WindowsAdapter) -> None:
    assert adapter.modifier_key() == "ctrl"


def test_clipboard_copy(adapter: WindowsAdapter) -> None:
    with patch("desktop.platform.win.pyautogui.hotkey") as mock_hotkey:
        adapter.clipboard_copy()
    mock_hotkey.assert_called_once_with("ctrl", "c")


def test_clipboard_paste(adapter: WindowsAdapter) -> None:
    with patch("desktop.platform.win.pyautogui.hotkey") as mock_hotkey:
        adapter.clipboard_paste()
    mock_hotkey.assert_called_once_with("ctrl", "v")


def test_import_win_nao_falha_em_macos() -> None:
    """win.py deve ser importável em macOS sem pygetwindow instalado."""
    import desktop.platform.win  # noqa: F401 — apenas testa que não lança ImportError
