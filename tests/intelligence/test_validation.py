"""Testes de intelligence.validation."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

import pytest
from pydantic import BaseModel, ConfigDict, Field, field_validator

from intelligence.exceptions import ValidationCodeError
from intelligence.validation import validate


class _SimpleSchema(BaseModel):
    name: str
    amount: Annotated[Decimal, Field(ge=0)]


class _StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: int


class _BuggySchema(BaseModel):
    y: int

    @field_validator("y")
    @classmethod
    def _explode(cls, v: int) -> int:
        raise TypeError("validador quebrado")


def test_valid_returns_is_valid_true_and_model() -> None:
    r = validate({"name": "abc", "amount": "10.50"}, _SimpleSchema)
    assert r.is_valid is True
    assert r.model is not None
    assert isinstance(r.model, _SimpleSchema)
    assert r.model.amount == Decimal("10.50")


def test_none_data_returns_payload_vazio() -> None:
    r = validate(None, _SimpleSchema)
    assert r.is_valid is False
    assert r.errors == ["payload vazio"]


def test_missing_field_appears_in_errors() -> None:
    r = validate({"amount": "1"}, _SimpleSchema)
    assert r.is_valid is False
    assert any("name" in e for e in r.errors)


def test_wrong_type_appears_in_errors() -> None:
    r = validate({"name": "x", "amount": "abc"}, _SimpleSchema)
    assert r.is_valid is False
    assert any("amount" in e for e in r.errors)


def test_negative_value_appears_in_errors() -> None:
    r = validate({"name": "x", "amount": "-1"}, _SimpleSchema)
    assert r.is_valid is False
    assert any("amount" in e for e in r.errors)


def test_extra_forbid_rejects_extras() -> None:
    r = validate({"x": 1, "extra": "no"}, _StrictSchema)
    assert r.is_valid is False
    assert any("extra" in e for e in r.errors)


def test_error_format_field_colon_msg() -> None:
    r = validate({"amount": "1"}, _SimpleSchema)
    assert all(":" in e for e in r.errors)


def test_buggy_validator_raises_validation_code_error() -> None:
    with pytest.raises(ValidationCodeError) as excinfo:
        validate({"y": 1}, _BuggySchema)
    assert excinfo.value.schema == "_BuggySchema"
    assert isinstance(excinfo.value.original_exception, TypeError)


def test_valid_empty_dict_for_no_required_fields() -> None:
    class _Empty(BaseModel):
        pass

    r = validate({}, _Empty)
    assert r.is_valid is True


def test_model_attribute_is_none_when_invalid() -> None:
    r = validate({}, _SimpleSchema)
    assert r.model is None
    assert r.warnings == []
