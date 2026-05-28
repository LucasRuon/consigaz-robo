"""Testes unitários para web/session.py (sem browser real)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from web.exceptions import LoginRequiredError
from web.session import _profile_path, close_browser, open_browser


@pytest.fixture()
def settings() -> MagicMock:
    s = MagicMock()
    s.web_headless = False
    s.web_user_agent = "Mozilla/5.0"
    s.web_viewport_width = 1280
    s.web_viewport_height = 800
    s.web_locale = "pt-BR"
    s.web_login_url_patterns = ["/login", "/auth", "/signin", "/entrar"]
    return s


@pytest.fixture()
def mock_playwright(settings: MagicMock):
    """Configura mock completo do playwright."""
    with patch("playwright.sync_api.sync_playwright") as mock_pw:
        mock_page = MagicMock()
        mock_page.url = "https://app.consigaz.com.br/dashboard"
        mock_page.locator.return_value.wait_for = MagicMock()

        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page

        mock_chromium = MagicMock()
        mock_chromium.launch_persistent_context.return_value = mock_context

        mock_instance = MagicMock()
        mock_instance.chromium = mock_chromium

        mock_pw.return_value.start.return_value = mock_instance
        yield mock_pw, mock_instance, mock_context, mock_page


class TestProfilePath:
    def test_returns_path(self) -> None:
        p = _profile_path()
        assert isinstance(p, Path)

    def test_contains_consigaz_robo(self) -> None:
        p = _profile_path()
        assert ".consigaz-robo" in str(p)

    def test_contains_playwright_profile(self) -> None:
        p = _profile_path()
        assert "playwright-profile" in str(p)

    def test_under_home(self) -> None:
        p = _profile_path()
        assert str(p).startswith(str(Path.home()))


class TestOpenBrowser:
    def test_returns_page(self, mock_playwright, settings: MagicMock) -> None:
        _, _, _, mock_page = mock_playwright
        page = open_browser(settings)
        assert page is mock_page

    def test_launch_with_headless_flag(
        self, mock_playwright, settings: MagicMock
    ) -> None:
        _, mock_instance, _, _ = mock_playwright
        open_browser(settings)
        call_kwargs = mock_instance.chromium.launch_persistent_context.call_args
        assert call_kwargs.kwargs["headless"] is False

    def test_launch_with_user_agent(
        self, mock_playwright, settings: MagicMock
    ) -> None:
        _, mock_instance, _, _ = mock_playwright
        open_browser(settings)
        call_kwargs = mock_instance.chromium.launch_persistent_context.call_args
        assert call_kwargs.kwargs["user_agent"] == "Mozilla/5.0"

    def test_launch_with_locale(self, mock_playwright, settings: MagicMock) -> None:
        _, mock_instance, _, _ = mock_playwright
        open_browser(settings)
        call_kwargs = mock_instance.chromium.launch_persistent_context.call_args
        assert call_kwargs.kwargs["locale"] == "pt-BR"

    def test_login_required_error_on_login_url(
        self, mock_playwright, settings: MagicMock
    ) -> None:
        _, _, _, mock_page = mock_playwright
        mock_page.url = "https://app.consigaz.com.br/login"
        with pytest.raises(LoginRequiredError) as exc_info:
            open_browser(settings)
        assert exc_info.value.current_url == "https://app.consigaz.com.br/login"

    def test_sentinel_timeout_raises_login_required(
        self, mock_playwright, settings: MagicMock
    ) -> None:
        _, _, _, mock_page = mock_playwright
        mock_page.url = "https://app.consigaz.com.br/dashboard"
        mock_page.locator.return_value.wait_for.side_effect = Exception("timeout")
        selectors = {"login": {"_session_sentinel": "#app-main"}}
        with pytest.raises(LoginRequiredError):
            open_browser(settings, selectors)

    def test_no_sentinel_check_when_absent(
        self, mock_playwright, settings: MagicMock
    ) -> None:
        _, _, _, mock_page = mock_playwright
        mock_page.url = "https://app.consigaz.com.br/dashboard"
        selectors: dict[str, dict[str, str]] = {}
        page = open_browser(settings, selectors)
        assert page is mock_page


class TestCloseBrowser:
    def test_no_op_when_not_opened(self) -> None:
        import web.session as sess

        sess._context = None
        sess._playwright_instance = None
        close_browser()

    def test_closes_context(self, mock_playwright, settings: MagicMock) -> None:
        _, _, mock_context, _ = mock_playwright
        open_browser(settings)
        close_browser()
        mock_context.close.assert_called_once()

    def test_context_is_none_after_close(
        self, mock_playwright, settings: MagicMock
    ) -> None:
        import web.session as sess

        open_browser(settings)
        close_browser()
        assert sess._context is None
