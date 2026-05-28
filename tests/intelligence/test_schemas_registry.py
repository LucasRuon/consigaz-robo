"""Testes do registry de schemas."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from intelligence.exceptions import SchemaNotRegisteredError
from intelligence.schemas import get_schema, list_schemas, register


@pytest.mark.usefixtures("clear_schema_registry")
def test_register_and_get() -> None:
    @register("foo")
    class Foo(BaseModel):
        x: int

    assert get_schema("foo") is Foo


@pytest.mark.usefixtures("clear_schema_registry")
def test_get_unknown_raises() -> None:
    with pytest.raises(SchemaNotRegisteredError) as excinfo:
        get_schema("inexistente")
    assert excinfo.value.name == "inexistente"
    assert excinfo.value.known == []


@pytest.mark.usefixtures("clear_schema_registry")
def test_register_returns_class() -> None:
    @register("bar")
    class Bar(BaseModel):
        y: str

    assert Bar.__name__ == "Bar"


@pytest.mark.usefixtures("clear_schema_registry")
def test_re_register_same_class_is_noop() -> None:
    class Baz(BaseModel):
        pass

    register("baz")(Baz)
    register("baz")(Baz)  # não deve lançar
    assert get_schema("baz") is Baz


@pytest.mark.usefixtures("clear_schema_registry")
def test_re_register_different_class_raises() -> None:
    class A(BaseModel):
        pass

    class B(BaseModel):
        pass

    register("conflict")(A)
    with pytest.raises(RuntimeError, match="já registrado"):
        register("conflict")(B)


@pytest.mark.usefixtures("clear_schema_registry")
def test_list_schemas_sorted() -> None:
    @register("zebra")
    class _Z(BaseModel):
        pass

    @register("alpha")
    class _A(BaseModel):
        pass

    assert list_schemas() == ["alpha", "zebra"]


@pytest.mark.usefixtures("clear_schema_registry")
def test_list_schemas_empty() -> None:
    assert list_schemas() == []


@pytest.mark.usefixtures("clear_schema_registry")
def test_known_in_error_is_sorted() -> None:
    @register("z")
    class _Z(BaseModel):
        pass

    @register("a")
    class _A(BaseModel):
        pass

    with pytest.raises(SchemaNotRegisteredError) as excinfo:
        get_schema("nope")
    assert excinfo.value.known == ["a", "z"]
