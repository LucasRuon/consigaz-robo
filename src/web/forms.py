"""Preenchimento de formulários e captura de dados (Playwright sync API)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from web.exceptions import SelectorNotFoundError, TransactionError, WebError
from web.selectors import get_selector

if TYPE_CHECKING:
    from playwright.sync_api import Page

_MODAL_SELECTORS = [
    "[aria-label*='fechar' i]",
    "[aria-label*='close' i]",
    "button:has-text('OK')",
    "button:has-text('Fechar')",
    "button:has-text('Entendi')",
]


def fill_form(
    page: Page,
    selectors: dict[str, dict[str, str]],
    page_name: str,
    data: dict[str, str | None],
) -> None:
    """Preenche campos do formulário via mapeamento JSON."""
    try:
        for key, value in data.items():
            if key.startswith("_"):
                continue
            if value is None:
                continue
            selector = get_selector(selectors, page_name, key)
            locator = page.locator(selector).first
            tag: str = locator.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                locator.select_option(value=value)
            else:
                locator.fill("")
                locator.fill(value)
    except SelectorNotFoundError:
        raise
    except Exception as exc:
        raise WebError(f"Falha ao preencher formulário '{page_name}': {exc}") from exc


def handle_modal(page: Page) -> bool:
    """Fecha modal se presente; retorna True se fechou, False caso contrário."""
    for sel in _MODAL_SELECTORS:
        try:
            locator = page.locator(sel).first
            if locator.is_visible():
                locator.click()
                return True
        except Exception:
            continue
    return False


def capture_transaction_id(
    page: Page,
    selectors: dict[str, dict[str, str]],
    page_name: str,
    key: str,
) -> str:
    """Extrai texto do campo; lança TransactionError se vazio."""
    selector = get_selector(selectors, page_name, key)
    text: str = page.locator(selector).first.inner_text()
    if not text or not text.strip():
        raise TransactionError(page_name, key)
    return text.strip()
