"""Fixtures compartilhadas dos testes de intelligence."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from intelligence import schemas as _schemas_module


@pytest.fixture
def clear_schema_registry() -> Iterator[None]:
    """Limpa o registry de schemas antes/depois de cada teste que usa."""
    _schemas_module._clear_registry_for_tests()
    yield
    _schemas_module._clear_registry_for_tests()
