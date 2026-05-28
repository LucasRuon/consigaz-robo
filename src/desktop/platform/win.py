"""WindowsAdapter: implementação de PlatformAdapter para Windows via pygetwindow/subprocess."""

from __future__ import annotations

import subprocess

import pyautogui

from desktop.exceptions import PlatformError


class WindowsAdapter:
    """Adapter de plataforma para Windows: usa subprocess.Popen e pygetwindow."""

    def launch_app(self, app_name: str) -> None:
        try:
            subprocess.Popen([app_name])
        except FileNotFoundError as exc:
            raise PlatformError(f"Executável não encontrado: {app_name!r}") from exc

    def focus_window(self, app_name: str) -> None:
        import pygetwindow as gw  # lazy — só instalado no Windows

        windows = gw.getWindowsWithTitle(app_name)
        if not windows:
            raise PlatformError(f"Janela não encontrada: {app_name!r}")
        try:
            windows[0].activate()
        except Exception as exc:
            raise PlatformError(f"Falha ao ativar janela {app_name!r}") from exc

    def modifier_key(self) -> str:
        return "ctrl"

    def clipboard_copy(self) -> None:
        pyautogui.hotkey("ctrl", "c")

    def clipboard_paste(self) -> None:
        pyautogui.hotkey("ctrl", "v")
