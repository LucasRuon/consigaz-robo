"""Gerenciamento de sessão do browser (Playwright sync API)."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from web.exceptions import LoginRequiredError

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page

    from config.settings import Settings

_context: BrowserContext | None = None
_playwright_instance: Any = None


def _profile_path() -> Path:
    return Path.home() / ".consigaz-robo" / "playwright-profile"


def open_browser(
    settings: Settings,
    selectors: dict[str, dict[str, str]] | None = None,
) -> Page:
    """Abre chromium com perfil persistido; retorna Page pronta para uso."""
    from playwright.sync_api import sync_playwright  # lazy import

    global _context, _playwright_instance

    profile = _profile_path()
    profile.mkdir(parents=True, exist_ok=True)

    pw = sync_playwright().start()
    _playwright_instance = pw

    _context = pw.chromium.launch_persistent_context(
        user_data_dir=str(profile),
        headless=settings.web_headless,
        user_agent=settings.web_user_agent,
        viewport={
            "width": settings.web_viewport_width,
            "height": settings.web_viewport_height,
        },
        locale=settings.web_locale,
    )

    page: Page = _context.new_page()

    _check_session(page, selectors or {}, settings)

    return page


def close_browser() -> None:
    """Fecha contexto; no-op se não aberto."""
    global _context, _playwright_instance

    if _context is not None:
        _context.close()
        _context = None

    if _playwright_instance is not None:
        with contextlib.suppress(Exception):
            _playwright_instance.stop()
        _playwright_instance = None


def _check_session(
    page: Page,
    selectors: dict[str, dict[str, str]],
    settings: Settings,
) -> None:
    """Lança LoginRequiredError se sessão expirada (URL ou sentinel)."""
    url = page.url
    for pattern in settings.web_login_url_patterns:
        if pattern in url:
            raise LoginRequiredError(url)

    sentinel = selectors.get("login", {}).get("_session_sentinel")
    if sentinel:
        try:
            page.locator(sentinel).wait_for(timeout=3000)
        except Exception as exc:
            raise LoginRequiredError(url) from exc
