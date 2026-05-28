"""Primitivas de interação de UI: click, type, clear, extract via clipboard."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pyautogui
import pyperclip

from desktop.exceptions import InteractionError
from desktop.vision import wait_for_template

if TYPE_CHECKING:
    from desktop.platform.adapter import PlatformAdapter


def click_at_template(path: str | Path) -> None:
    """Clica no centro do template encontrado na tela."""
    try:
        x, y = wait_for_template(path)
        pyautogui.click(x, y)
    except Exception as exc:
        raise InteractionError("click_at_template", str(path)) from exc


def type_text(text: str) -> None:
    """Digita texto com intervalo entre teclas. No-op para string vazia."""
    if not text:
        return
    try:
        pyautogui.write(text, interval=0.05)
    except Exception as exc:
        raise InteractionError("type_text") from exc


def clear_field(adapter: PlatformAdapter) -> None:
    """Seleciona tudo e deleta o conteúdo do campo atual."""
    try:
        pyautogui.hotkey(adapter.modifier_key(), "a")
        pyautogui.press("delete")
    except Exception as exc:
        raise InteractionError("clear_field") from exc


def extract_via_clipboard(adapter: PlatformAdapter) -> str:
    """Seleciona tudo, copia para clipboard e retorna o texto. Retorna '' se vazio."""
    try:
        pyautogui.hotkey(adapter.modifier_key(), "a")
        adapter.clipboard_copy()
        return str(pyperclip.paste())
    except Exception as exc:
        raise InteractionError("extract_via_clipboard") from exc
