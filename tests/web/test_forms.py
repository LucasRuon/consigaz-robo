"""Testes unitários para web/forms.py (sem browser real)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from web.exceptions import SelectorNotFoundError, TransactionError, WebError
from web.forms import capture_transaction_id, fill_form, handle_modal


@pytest.fixture()
def selectors() -> dict[str, dict[str, str]]:
    return {
        "cadastro": {
            "nome": "#nome",
            "tipo": "select#tipo",
            "_meta": "#ignored",
        },
        "confirmacao": {
            "id_protocolo": "#protocolo",
        },
    }


@pytest.fixture()
def mock_page() -> MagicMock:
    page = MagicMock()
    locator = MagicMock()
    locator.evaluate.return_value = "input"
    locator.fill = MagicMock()
    locator.select_option = MagicMock()
    locator.inner_text.return_value = "TXN-12345"
    locator.is_visible.return_value = False
    page.locator.return_value.first = locator
    return page


class TestFillForm:
    def test_fill_ok(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        fill_form(mock_page, selectors, "cadastro", {"nome": "João"})
        mock_page.locator.assert_called_with("#nome")
        mock_page.locator.return_value.first.fill.assert_called_with("João")

    def test_fill_clears_before_filling(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        fill_form(mock_page, selectors, "cadastro", {"nome": "João"})
        locator = mock_page.locator.return_value.first
        calls = locator.fill.call_args_list
        assert calls[0].args[0] == ""
        assert calls[1].args[0] == "João"

    def test_fill_none_skips_field(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        fill_form(mock_page, selectors, "cadastro", {"nome": None})
        mock_page.locator.return_value.first.fill.assert_not_called()

    def test_fill_select_uses_select_option(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        mock_page.locator.return_value.first.evaluate.return_value = "select"
        fill_form(mock_page, selectors, "cadastro", {"tipo": "opcao_a"})
        mock_page.locator.return_value.first.select_option.assert_called_with(
            value="opcao_a"
        )

    def test_fill_missing_key_raises_selector_not_found(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        with pytest.raises(SelectorNotFoundError) as exc_info:
            fill_form(mock_page, selectors, "cadastro", {"campo_inexistente": "x"})
        assert exc_info.value.key == "campo_inexistente"

    def test_fill_ignores_underscore_keys(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        fill_form(mock_page, selectors, "cadastro", {"_meta": "valor"})
        mock_page.locator.return_value.first.fill.assert_not_called()

    def test_fill_empty_data(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        fill_form(mock_page, selectors, "cadastro", {})
        mock_page.locator.return_value.first.fill.assert_not_called()

    def test_fill_playwright_error_raises_web_error(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        mock_page.locator.return_value.first.evaluate.side_effect = RuntimeError(
            "browser crashed"
        )
        with pytest.raises(WebError, match="Falha ao preencher"):
            fill_form(mock_page, selectors, "cadastro", {"nome": "João"})


class TestHandleModal:
    def test_no_modal_returns_false(self, mock_page: MagicMock) -> None:
        mock_page.locator.return_value.first.is_visible.return_value = False
        result = handle_modal(mock_page)
        assert result is False

    def test_modal_found_returns_true(self, mock_page: MagicMock) -> None:
        mock_page.locator.return_value.first.is_visible.return_value = True
        result = handle_modal(mock_page)
        assert result is True
        mock_page.locator.return_value.first.click.assert_called_once()

    def test_exception_in_locator_continues(self, mock_page: MagicMock) -> None:
        mock_page.locator.side_effect = [
            RuntimeError("locator error"),
            mock_page.locator.return_value,
        ]
        mock_page.locator.return_value.first.is_visible.return_value = True
        result = handle_modal(mock_page)
        assert result is True


class TestCaptureTransactionId:
    def test_capture_ok(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        result = capture_transaction_id(mock_page, selectors, "confirmacao", "id_protocolo")
        assert result == "TXN-12345"

    def test_empty_text_raises_transaction_error(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        mock_page.locator.return_value.first.inner_text.return_value = ""
        with pytest.raises(TransactionError) as exc_info:
            capture_transaction_id(mock_page, selectors, "confirmacao", "id_protocolo")
        assert exc_info.value.page == "confirmacao"
        assert exc_info.value.key == "id_protocolo"

    def test_whitespace_text_raises_transaction_error(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        mock_page.locator.return_value.first.inner_text.return_value = "   "
        with pytest.raises(TransactionError):
            capture_transaction_id(mock_page, selectors, "confirmacao", "id_protocolo")

    def test_missing_key_raises_selector_not_found(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        with pytest.raises(SelectorNotFoundError):
            capture_transaction_id(mock_page, selectors, "confirmacao", "chave_inexistente")
