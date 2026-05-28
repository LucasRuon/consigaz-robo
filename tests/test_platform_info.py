"""Testes para src/platform_info.py."""

from __future__ import annotations

import importlib
import sys

import pytest

import platform_info
from platform_info import (
    MODIFIER_KEY,
    Platform,
    UnsupportedPlatformError,
    current_platform,
    is_supported,
)


def test_darwin_detecta_platform_e_e_suportado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platform_info.platform, "machine", lambda: "arm64")
    assert current_platform() is Platform.DARWIN
    assert is_supported() is True


def test_darwin_x86_64_tambem_suportado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platform_info.platform, "machine", lambda: "x86_64")
    assert current_platform() is Platform.DARWIN
    assert is_supported() is True


def test_windows_amd64_suportado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(platform_info.platform, "machine", lambda: "AMD64")
    assert current_platform() is Platform.WIN32
    assert is_supported() is True


def test_windows_arm64_nao_suportado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(platform_info.platform, "machine", lambda: "ARM64")
    assert current_platform() is Platform.WIN32
    assert is_supported() is False


def test_linux_lanca_unsupported_platform_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(platform_info.platform, "machine", lambda: "x86_64")
    with pytest.raises(UnsupportedPlatformError):
        current_platform()
    assert is_supported() is False


def test_freebsd_lanca_unsupported_platform_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "freebsd13")
    with pytest.raises(UnsupportedPlatformError):
        current_platform()
    assert is_supported() is False


def test_unsupported_platform_error_e_runtime_error() -> None:
    assert issubclass(UnsupportedPlatformError, RuntimeError)


def test_modifier_key_em_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    reloaded = importlib.reload(platform_info)
    try:
        assert reloaded.MODIFIER_KEY == "cmd"
    finally:
        monkeypatch.setattr(sys, "platform", sys.platform)
        importlib.reload(platform_info)


def test_modifier_key_em_win32(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    reloaded = importlib.reload(platform_info)
    try:
        assert reloaded.MODIFIER_KEY == "ctrl"
    finally:
        importlib.reload(platform_info)


def test_modifier_key_em_plataforma_nao_suportada_e_vazio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    reloaded = importlib.reload(platform_info)
    try:
        assert reloaded.MODIFIER_KEY == ""
    finally:
        importlib.reload(platform_info)


def test_modifier_key_constante_modulo_existe() -> None:
    assert isinstance(MODIFIER_KEY, str)
