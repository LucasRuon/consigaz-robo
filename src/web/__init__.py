"""Módulo Web — Playwright sync API com sessão persistida."""

from web.exceptions import (
    LoginRequiredError,
    PageLoadTimeoutError,
    SelectorLoadError,
    SelectorNotFoundError,
    TransactionError,
    WebError,
)
from web.forms import capture_transaction_id, fill_form, handle_modal
from web.navigation import navigate_to, wait_for_selector
from web.selectors import get_selector, load_selectors
from web.session import close_browser, open_browser

__all__ = [
    "LoginRequiredError",
    "PageLoadTimeoutError",
    "SelectorLoadError",
    "SelectorNotFoundError",
    "TransactionError",
    "WebError",
    "capture_transaction_id",
    "close_browser",
    "fill_form",
    "get_selector",
    "handle_modal",
    "load_selectors",
    "navigate_to",
    "open_browser",
    "wait_for_selector",
]
