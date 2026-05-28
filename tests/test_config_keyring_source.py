"""Testes do KeyringSettingsSource."""
from __future__ import annotations

from typing import Any

import pytest
from keyring.errors import KeyringError
from pydantic_settings import BaseSettings

from config.keyring_source import KEYRING_SERVICE, KeyringSettingsSource


class _FakeSettings(BaseSettings):
    foo: str | None = None
    bar: str | None = None


def test_keyring_service_constant() -> None:
    assert KEYRING_SERVICE == "consigaz-robo"


def test_returns_values_for_all_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    stored = {"foo": "valor1", "bar": "valor2"}

    def fake_get_password(service: str, name: str) -> str | None:
        assert service == KEYRING_SERVICE
        return stored.get(name)

    monkeypatch.setattr("keyring.get_password", fake_get_password)

    source = KeyringSettingsSource(_FakeSettings)
    result = source()

    assert result == {"foo": "valor1", "bar": "valor2"}


def test_returns_empty_when_no_values(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_password(service: str, name: str) -> str | None:
        return None

    monkeypatch.setattr("keyring.get_password", fake_get_password)

    source = KeyringSettingsSource(_FakeSettings)
    result = source()

    assert result == {}


def test_returns_empty_on_keyring_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_password(service: str, name: str) -> str | None:
        raise KeyringError("backend indisponível")

    monkeypatch.setattr("keyring.get_password", fake_get_password)

    source = KeyringSettingsSource(_FakeSettings)
    result = source()

    assert result == {}


def test_mixed_some_present_some_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict[str, str] = {"foo": "valor1"}

    def fake_get_password(service: str, name: str) -> str | None:
        return stored.get(name)

    monkeypatch.setattr("keyring.get_password", fake_get_password)

    source = KeyringSettingsSource(_FakeSettings)
    result = source()

    assert result == {"foo": "valor1"}


def test_propagates_non_keyring_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_password(service: str, name: str) -> str | None:
        raise RuntimeError("bug real")

    monkeypatch.setattr("keyring.get_password", fake_get_password)

    source = KeyringSettingsSource(_FakeSettings)
    with pytest.raises(RuntimeError, match="bug real"):
        source()


def test_get_field_value_returns_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_password(service: str, name: str) -> str | None:
        return "x" if name == "foo" else None

    monkeypatch.setattr("keyring.get_password", fake_get_password)

    source = KeyringSettingsSource(_FakeSettings)
    field = _FakeSettings.model_fields["foo"]
    value, name, is_complex = source.get_field_value(field, "foo")
    assert value == "x"
    assert name == "foo"
    assert is_complex is False

    value2: Any
    value2, name2, _ = source.get_field_value(_FakeSettings.model_fields["bar"], "bar")
    assert value2 is None
    assert name2 == "bar"
