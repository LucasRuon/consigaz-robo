"""Testes de `orchestrator.exceptions`."""

from __future__ import annotations

from orchestrator.exceptions import (
    RoutineNameError,
    RoutineRegistryError,
    UnknownRoutineError,
)


def test_registry_error_eh_exception() -> None:
    err = RoutineRegistryError("foo")
    assert isinstance(err, Exception)
    assert "foo" in str(err)


def test_name_error_guarda_nome() -> None:
    err = RoutineNameError("BAD/NAME")
    assert err.name == "BAD/NAME"
    assert "BAD/NAME" in str(err)


def test_unknown_routine_formata_available() -> None:
    err = UnknownRoutineError("xyz", available=["a", "b"])
    msg = str(err)
    assert "xyz" in msg
    assert "a" in msg and "b" in msg
    assert err.available == ["a", "b"]


def test_unknown_routine_sem_available() -> None:
    err = UnknownRoutineError("xyz")
    assert "xyz" in str(err)
    assert err.available == []
