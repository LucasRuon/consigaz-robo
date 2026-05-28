"""PlatformAdapter Protocol e factory get_platform_adapter()."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Protocol

from desktop.exceptions import UnsupportedPlatformError

if TYPE_CHECKING:
    pass


class PlatformAdapter(Protocol):
    """Interface de abstração de plataforma para operações de desktop."""

    def launch_app(self, app_name: str) -> None: ...
    def focus_window(self, app_name: str) -> None: ...
    def modifier_key(self) -> str: ...
    def clipboard_copy(self) -> None: ...
    def clipboard_paste(self) -> None: ...


def get_platform_adapter() -> PlatformAdapter:
    """Factory: retorna MacAdapter em darwin, WindowsAdapter em win32."""
    if sys.platform == "darwin":
        from desktop.platform.mac import MacAdapter  # lazy — evita ImportError em Windows

        return MacAdapter()
    if sys.platform == "win32":
        from desktop.platform.win import WindowsAdapter  # lazy — evita ImportError em macOS

        return WindowsAdapter()
    raise UnsupportedPlatformError(f"Plataforma não suportada pelo módulo Desktop: {sys.platform!r}")
