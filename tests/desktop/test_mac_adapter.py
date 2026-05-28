"""Testes unitários do MacAdapter com mock de subprocess e pyautogui."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, call, patch

import pytest

from desktop.exceptions import PlatformError
from desktop.platform.mac import MacAdapter


@pytest.fixture()
def adapter() -> MacAdapter:
    return MacAdapter()


def test_launch_app_chama_open_a(adapter: MacAdapter) -> None:
    with patch("desktop.platform.mac.subprocess.run") as mock_run:
        adapter.launch_app("MeuApp")
    mock_run.assert_called_once_with(
        ["open", "-a", "MeuApp"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_launch_app_falha_lanca_platform_error(adapter: MacAdapter) -> None:
    err = subprocess.CalledProcessError(1, "open", stderr="app not found")
    with patch("desktop.platform.mac.subprocess.run", side_effect=err):
        with pytest.raises(PlatformError, match="MeuApp"):
            adapter.launch_app("MeuApp")


def test_focus_window_executa_applescript(adapter: MacAdapter) -> None:
    with patch("desktop.platform.mac.subprocess.run") as mock_run:
        adapter.focus_window("MeuApp")
    args = mock_run.call_args[0][0]
    assert args[0] == "osascript"
    assert "MeuApp" in args[-1]
    assert "activate" in args[-1]


def test_focus_window_falha_lanca_platform_error(adapter: MacAdapter) -> None:
    err = subprocess.CalledProcessError(1, "osascript", stderr="no window")
    with patch("desktop.platform.mac.subprocess.run", side_effect=err):
        with pytest.raises(PlatformError, match="MeuApp"):
            adapter.focus_window("MeuApp")


def test_modifier_key_retorna_cmd(adapter: MacAdapter) -> None:
    assert adapter.modifier_key() == "cmd"


def test_clipboard_copy(adapter: MacAdapter) -> None:
    with patch("desktop.platform.mac.pyautogui.hotkey") as mock_hotkey:
        adapter.clipboard_copy()
    mock_hotkey.assert_called_once_with("command", "c")


def test_clipboard_paste(adapter: MacAdapter) -> None:
    with patch("desktop.platform.mac.pyautogui.hotkey") as mock_hotkey:
        adapter.clipboard_paste()
    mock_hotkey.assert_called_once_with("command", "v")
