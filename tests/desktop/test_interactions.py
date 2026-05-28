"""Testes unitários das primitivas de UI com mocks de pyautogui e pyperclip."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from desktop.exceptions import InteractionError
from desktop.interactions import (
    clear_field,
    click_at_template,
    extract_via_clipboard,
    type_text,
)


@pytest.fixture()
def mock_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.modifier_key.return_value = "cmd"
    return adapter


# --- click_at_template ---

def test_click_at_template_chama_wait_e_click(tmp_path: Path) -> None:
    with (
        patch("desktop.interactions.wait_for_template", return_value=(50, 80)) as mock_wait,
        patch("desktop.interactions.pyautogui.click") as mock_click,
    ):
        click_at_template("btn.png")
    mock_wait.assert_called_once_with("btn.png")
    mock_click.assert_called_once_with(50, 80)


def test_click_at_template_falha_lanca_interaction_error() -> None:
    with patch("desktop.interactions.wait_for_template", side_effect=RuntimeError("sem match")):
        with pytest.raises(InteractionError) as exc_info:
            click_at_template("btn.png")
    assert exc_info.value.action == "click_at_template"
    assert "btn.png" in (exc_info.value.template_path or "")


# --- type_text ---

def test_type_text_chama_write_com_interval() -> None:
    with patch("desktop.interactions.pyautogui.write") as mock_write:
        type_text("hello")
    mock_write.assert_called_once_with("hello", interval=0.05)


def test_type_text_vazio_e_noop() -> None:
    with patch("desktop.interactions.pyautogui.write") as mock_write:
        type_text("")
    mock_write.assert_not_called()


def test_type_text_falha_lanca_interaction_error() -> None:
    with patch("desktop.interactions.pyautogui.write", side_effect=OSError("sem acesso")):
        with pytest.raises(InteractionError) as exc_info:
            type_text("texto")
    assert exc_info.value.action == "type_text"


# --- clear_field ---

def test_clear_field_usa_modifier_e_delete(mock_adapter: MagicMock) -> None:
    with (
        patch("desktop.interactions.pyautogui.hotkey") as mock_hotkey,
        patch("desktop.interactions.pyautogui.press") as mock_press,
    ):
        clear_field(mock_adapter)
    mock_hotkey.assert_called_once_with("cmd", "a")
    mock_press.assert_called_once_with("delete")


def test_clear_field_falha_lanca_interaction_error(mock_adapter: MagicMock) -> None:
    with patch("desktop.interactions.pyautogui.hotkey", side_effect=OSError("sem acesso")):
        with pytest.raises(InteractionError) as exc_info:
            clear_field(mock_adapter)
    assert exc_info.value.action == "clear_field"


# --- extract_via_clipboard ---

def test_extract_via_clipboard_retorna_texto(mock_adapter: MagicMock) -> None:
    with (
        patch("desktop.interactions.pyautogui.hotkey"),
        patch("desktop.interactions.pyperclip.paste", return_value="texto copiado"),
    ):
        result = extract_via_clipboard(mock_adapter)
    assert result == "texto copiado"


def test_extract_via_clipboard_retorna_vazio_sem_excecao(mock_adapter: MagicMock) -> None:
    with (
        patch("desktop.interactions.pyautogui.hotkey"),
        patch("desktop.interactions.pyperclip.paste", return_value=""),
    ):
        result = extract_via_clipboard(mock_adapter)
    assert result == ""


def test_extract_via_clipboard_chama_clipboard_copy(mock_adapter: MagicMock) -> None:
    with (
        patch("desktop.interactions.pyautogui.hotkey"),
        patch("desktop.interactions.pyperclip.paste", return_value="x"),
    ):
        extract_via_clipboard(mock_adapter)
    mock_adapter.clipboard_copy.assert_called_once()


def test_extract_via_clipboard_falha_lanca_interaction_error(mock_adapter: MagicMock) -> None:
    with patch("desktop.interactions.pyautogui.hotkey", side_effect=OSError("sem acesso")):
        with pytest.raises(InteractionError) as exc_info:
            extract_via_clipboard(mock_adapter)
    assert exc_info.value.action == "extract_via_clipboard"
