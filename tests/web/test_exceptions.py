"""Testes unitários para web/exceptions.py."""

from __future__ import annotations

import pytest

from web.exceptions import (
    LoginRequiredError,
    PageLoadTimeoutError,
    SelectorLoadError,
    SelectorNotFoundError,
    TransactionError,
    WebError,
)


class TestWebError:
    def test_is_runtime_error(self) -> None:
        assert issubclass(WebError, RuntimeError)

    def test_instantiate(self) -> None:
        e = WebError("falha")
        assert str(e) == "falha"


class TestLoginRequiredError:
    def test_is_web_error(self) -> None:
        assert issubclass(LoginRequiredError, WebError)

    def test_attributes(self) -> None:
        e = LoginRequiredError("https://app.example.com/login")
        assert e.current_url == "https://app.example.com/login"

    def test_message_contains_url(self) -> None:
        e = LoginRequiredError("https://app.example.com/login")
        assert "https://app.example.com/login" in str(e)


class TestSelectorNotFoundError:
    def test_is_web_error(self) -> None:
        assert issubclass(SelectorNotFoundError, WebError)

    def test_attributes(self) -> None:
        e = SelectorNotFoundError("login", "username")
        assert e.page == "login"
        assert e.key == "username"

    def test_message(self) -> None:
        e = SelectorNotFoundError("login", "username")
        assert "login" in str(e)
        assert "username" in str(e)


class TestSelectorLoadError:
    def test_is_web_error(self) -> None:
        assert issubclass(SelectorLoadError, WebError)

    def test_attributes(self) -> None:
        e = SelectorLoadError("/path/to/selectors.json", "JSON inválido")
        assert e.path == "/path/to/selectors.json"
        assert e.reason == "JSON inválido"

    def test_message(self) -> None:
        e = SelectorLoadError("/path/selectors.json", "JSON inválido")
        assert "/path/selectors.json" in str(e)
        assert "JSON inválido" in str(e)


class TestPageLoadTimeoutError:
    def test_is_web_error(self) -> None:
        assert issubclass(PageLoadTimeoutError, WebError)

    def test_attributes(self) -> None:
        e = PageLoadTimeoutError("https://example.com", 30.5)
        assert e.url == "https://example.com"
        assert e.elapsed == pytest.approx(30.5)

    def test_message(self) -> None:
        e = PageLoadTimeoutError("https://example.com", 30.5)
        assert "https://example.com" in str(e)
        assert "30.5" in str(e)


class TestTransactionError:
    def test_is_web_error(self) -> None:
        assert issubclass(TransactionError, WebError)

    def test_attributes(self) -> None:
        e = TransactionError("confirmacao", "id_protocolo")
        assert e.page == "confirmacao"
        assert e.key == "id_protocolo"

    def test_message(self) -> None:
        e = TransactionError("confirmacao", "id_protocolo")
        assert "confirmacao" in str(e)
        assert "id_protocolo" in str(e)


class TestHierarchy:
    def test_all_subclass_web_error(self) -> None:
        for cls in [
            LoginRequiredError,
            SelectorNotFoundError,
            SelectorLoadError,
            PageLoadTimeoutError,
            TransactionError,
        ]:
            assert issubclass(cls, WebError)

    def test_all_subclass_runtime_error(self) -> None:
        for cls in [
            WebError,
            LoginRequiredError,
            SelectorNotFoundError,
            SelectorLoadError,
            PageLoadTimeoutError,
            TransactionError,
        ]:
            assert issubclass(cls, RuntimeError)

    def test_catch_via_web_error(self) -> None:
        with pytest.raises(WebError):
            raise LoginRequiredError("https://example.com")
