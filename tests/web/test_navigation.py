"""Testes unitários para web/navigation.py (sem browser real)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from web.exceptions import PageLoadTimeoutError, SelectorNotFoundError
from web.navigation import navigate_to, wait_for_selector


@pytest.fixture()
def mock_page() -> MagicMock:
    page = MagicMock()
    page.goto = MagicMock()
    page.locator.return_value.wait_for = MagicMock()
    return page


@pytest.fixture()
def selectors() -> dict[str, dict[str, str]]:
    return {
        "login": {
            "username": "input[name='username']",
            "submit": "button[type='submit']",
        }
    }


class TestNavigateTo:
    def test_navigate_ok(self, mock_page: MagicMock) -> None:
        navigate_to(mock_page, "https://example.com")
        mock_page.goto.assert_called_once_with(
            "https://example.com",
            wait_until="networkidle",
            timeout=30000,
        )

    def test_navigate_custom_timeout(self, mock_page: MagicMock) -> None:
        navigate_to(mock_page, "https://example.com", timeout=10.0)
        call_kwargs = mock_page.goto.call_args
        assert call_kwargs.kwargs["timeout"] == 10000

    def test_playwright_timeout_raises_page_load_timeout(
        self, mock_page: MagicMock
    ) -> None:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        mock_page.goto.side_effect = PlaywrightTimeoutError("timeout")
        with pytest.raises(PageLoadTimeoutError) as exc_info:
            navigate_to.__wrapped__(mock_page, "https://example.com", timeout=5.0)
        assert exc_info.value.url == "https://example.com"
        assert exc_info.value.elapsed >= 0

    def test_page_load_timeout_has_correct_url(self, mock_page: MagicMock) -> None:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        mock_page.goto.side_effect = PlaywrightTimeoutError("timeout")
        with pytest.raises(PageLoadTimeoutError) as exc_info:
            navigate_to.__wrapped__(mock_page, "https://slow.example.com")
        assert exc_info.value.url == "https://slow.example.com"

    def test_retry_on_page_load_timeout(self, mock_page: MagicMock) -> None:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        mock_page.goto.side_effect = [
            PlaywrightTimeoutError("timeout"),
            None,
        ]
        navigate_to(mock_page, "https://example.com")
        assert mock_page.goto.call_count == 2

    def test_retry_exhausted_raises_page_load_timeout(
        self, mock_page: MagicMock
    ) -> None:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        mock_page.goto.side_effect = PlaywrightTimeoutError("timeout")
        with pytest.raises(PageLoadTimeoutError):
            navigate_to(mock_page, "https://example.com")
        assert mock_page.goto.call_count == 3


class TestWaitForSelector:
    def test_wait_ok_returns_locator(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        locator = wait_for_selector(mock_page, selectors, "login", "username")
        assert locator is mock_page.locator.return_value

    def test_resolves_correct_selector(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        wait_for_selector(mock_page, selectors, "login", "username")
        mock_page.locator.assert_called_with("input[name='username']")

    def test_timeout_raises_selector_not_found(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        mock_page.locator.return_value.wait_for.side_effect = PlaywrightTimeoutError(
            "timeout"
        )
        with pytest.raises(SelectorNotFoundError) as exc_info:
            wait_for_selector(mock_page, selectors, "login", "username")
        assert exc_info.value.page == "login"
        assert exc_info.value.key == "username"

    def test_missing_page_raises_selector_not_found(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        with pytest.raises(SelectorNotFoundError) as exc_info:
            wait_for_selector(mock_page, selectors, "pagina_inexistente", "campo")
        assert exc_info.value.page == "pagina_inexistente"

    def test_missing_key_raises_selector_not_found(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        with pytest.raises(SelectorNotFoundError) as exc_info:
            wait_for_selector(mock_page, selectors, "login", "chave_inexistente")
        assert exc_info.value.key == "chave_inexistente"

    def test_custom_timeout_passed_to_wait_for(
        self, mock_page: MagicMock, selectors: dict[str, dict[str, str]]
    ) -> None:
        wait_for_selector(mock_page, selectors, "login", "username", timeout=5.0)
        mock_page.locator.return_value.wait_for.assert_called_with(
            state="visible", timeout=5000
        )
