"""Testes unitários da factory get_platform_adapter()."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from desktop.exceptions import UnsupportedPlatformError
from desktop.platform.adapter import PlatformAdapter, get_platform_adapter


def test_darwin_retorna_mac_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    mock_mac_instance = MagicMock()
    mock_mac_module = MagicMock()
    mock_mac_module.MacAdapter.return_value = mock_mac_instance
    with patch.dict("sys.modules", {"desktop.platform.mac": mock_mac_module}):
        adapter = get_platform_adapter()
    assert adapter is mock_mac_instance


def test_win32_retorna_windows_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "win32")
    mock_win_instance = MagicMock()
    mock_win_module = MagicMock()
    mock_win_module.WindowsAdapter.return_value = mock_win_instance
    with patch.dict("sys.modules", {"desktop.platform.win": mock_win_module}):
        adapter = get_platform_adapter()
    assert adapter is mock_win_instance


def test_linux_lanca_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    with pytest.raises(UnsupportedPlatformError):
        get_platform_adapter()


def test_linux_mensagem_contem_plataforma(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    with pytest.raises(UnsupportedPlatformError, match="linux"):
        get_platform_adapter()


def test_platform_adapter_e_protocol() -> None:
    import typing
    assert isinstance(PlatformAdapter, type(typing.Protocol))  # type: ignore[arg-type]
