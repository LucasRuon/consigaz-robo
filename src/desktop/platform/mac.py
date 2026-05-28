"""MacAdapter: implementação de PlatformAdapter para macOS via AppleScript/subprocess."""

from __future__ import annotations

import subprocess

import pyautogui

from desktop.exceptions import PlatformError


class MacAdapter:
    """Adapter de plataforma para macOS: usa `open -a` e AppleScript."""

    def launch_app(self, app_name: str) -> None:
        try:
            subprocess.run(
                ["open", "-a", app_name],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise PlatformError(
                f"Falha ao lançar app {app_name!r}: {exc.stderr.strip()}"
            ) from exc

    def focus_window(self, app_name: str) -> None:
        script = f'tell application "{app_name}" to activate'
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise PlatformError(
                f"Falha ao focar janela {app_name!r}: {exc.stderr.strip()}"
            ) from exc

    def modifier_key(self) -> str:
        return "cmd"

    def clipboard_copy(self) -> None:
        pyautogui.hotkey("command", "c")

    def clipboard_paste(self) -> None:
        pyautogui.hotkey("command", "v")
