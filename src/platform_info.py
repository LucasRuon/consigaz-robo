"""Detecção de plataforma (SO/arquitetura) suportada pelo robô."""

from __future__ import annotations

import platform
import sys
from enum import Enum


class UnsupportedPlatformError(RuntimeError):
    """SO ou arquitetura não suportados pelo robô."""


class Platform(Enum):
    DARWIN = "darwin"
    WIN32 = "win32"


def current_platform() -> Platform:
    """Detecta o SO atual; lança UnsupportedPlatformError em SO não suportado."""
    if sys.platform == "darwin":
        return Platform.DARWIN
    if sys.platform == "win32":
        return Platform.WIN32
    raise UnsupportedPlatformError(f"Plataforma não suportada: {sys.platform!r}")


def is_supported() -> bool:
    """True em macOS (qualquer arch) ou Windows x86_64; False em Linux ou Windows ARM64."""
    try:
        plat = current_platform()
    except UnsupportedPlatformError:
        return False
    return not (plat is Platform.WIN32 and platform.machine().upper() == "ARM64")


def _compute_modifier_key() -> str:
    try:
        plat = current_platform()
    except UnsupportedPlatformError:
        return ""
    if plat is Platform.DARWIN:
        return "cmd"
    return "ctrl"


MODIFIER_KEY: str = _compute_modifier_key()
