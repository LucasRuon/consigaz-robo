"""Navegação e espera por elementos (Playwright sync API)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from web.exceptions import PageLoadTimeoutError, SelectorNotFoundError
from web.selectors import get_selector

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(PageLoadTimeoutError),
    reraise=True,
)
def navigate_to(
    page: Page,
    url: str,
    timeout: float = 30.0,
) -> None:
    """Navega para URL e aguarda networkidle; lança PageLoadTimeoutError."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError  # lazy

    start = time.monotonic()
    try:
        page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
    except PlaywrightTimeoutError as exc:
        elapsed = time.monotonic() - start
        raise PageLoadTimeoutError(url=url, elapsed=elapsed) from exc


def wait_for_selector(
    page: Page,
    selectors: dict[str, dict[str, str]],
    page_name: str,
    key: str,
    timeout: float = 15.0,
) -> Locator:
    """Resolve seletor via get_selector() e aguarda visibilidade."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError  # lazy

    selector = get_selector(selectors, page_name, key)
    locator = page.locator(selector)
    try:
        locator.wait_for(state="visible", timeout=int(timeout * 1000))
    except PlaywrightTimeoutError as exc:
        raise SelectorNotFoundError(page_name, key) from exc
    return locator
