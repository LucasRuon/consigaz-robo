"""Exceções customizadas do módulo Web."""

from __future__ import annotations


class WebError(RuntimeError):
    """Base — qualquer falha do módulo web."""


class LoginRequiredError(WebError):
    """Sessão expirada ou não iniciada."""

    def __init__(self, current_url: str) -> None:
        super().__init__(f"Login necessário. URL atual: {current_url!r}")
        self.current_url = current_url


class SelectorNotFoundError(WebError):
    """Chave ou página ausente no selectors.json."""

    def __init__(self, page: str, key: str) -> None:
        super().__init__(f"Seletor não encontrado: página={page!r}, chave={key!r}")
        self.page = page
        self.key = key


class SelectorLoadError(WebError):
    """selectors.json malformado ou ilegível."""

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Falha ao carregar seletores de {path!r}: {reason}")
        self.path = path
        self.reason = reason


class PageLoadTimeoutError(WebError):
    """navigate_to excedeu timeout."""

    def __init__(self, url: str, elapsed: float) -> None:
        super().__init__(f"Timeout ao carregar {url!r} após {elapsed:.1f}s")
        self.url = url
        self.elapsed = elapsed


class TransactionError(WebError):
    """ID de transação vazio ou ausente."""

    def __init__(self, page: str, key: str) -> None:
        super().__init__(f"ID de transação vazio: página={page!r}, chave={key!r}")
        self.page = page
        self.key = key
