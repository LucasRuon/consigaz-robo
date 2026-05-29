"""Testes de `orchestrator.registry`."""

from __future__ import annotations

import sys

import pytest

from intelligence.types import Action
from orchestrator import registry
from orchestrator.context import RoutineContext
from orchestrator.exceptions import (
    RoutineNameError,
    RoutineRegistryError,
    UnknownRoutineError,
)
from orchestrator.types import RoutineResult


def _stub(ctx: RoutineContext) -> RoutineResult:
    return RoutineResult(action=Action.PROCEED_TO_WEB)


def test_register_e_get(clean_registry: None) -> None:
    registry.register("foo")(_stub)
    assert registry.get("foo") is _stub


def test_register_duplicado_lanca(clean_registry: None) -> None:
    registry.register("foo")(_stub)
    with pytest.raises(RoutineRegistryError):
        registry.register("foo")(_stub)


@pytest.mark.parametrize("bad", ["", "A", "1foo", "foo/bar", "foo..bar", "foo bar", "-foo"])
def test_nome_invalido_lanca(clean_registry: None, bad: str) -> None:
    with pytest.raises(RoutineNameError):
        registry.register(bad)(_stub)


def test_get_desconhecido_lanca_com_available(clean_registry: None) -> None:
    registry.register("a")(_stub)
    registry.register("b")(_stub)
    with pytest.raises(UnknownRoutineError) as exc:
        registry.get("z")
    assert exc.value.available == ["a", "b"]


def test_list_names_ordem_alfabetica(clean_registry: None) -> None:
    registry.register("zeta")(_stub)
    registry.register("alpha")(_stub)
    registry.register("mid")(_stub)
    assert registry.list_names() == ["alpha", "mid", "zeta"]


def test_discover_pacote_inexistente_nao_levanta(clean_registry: None) -> None:
    registry.discover("pacote_que_nao_existe_xyz_999")
    assert registry.list_names() == []


def test_discover_resiste_a_modulo_com_erro(
    clean_registry: None, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cria pacote-fixture: um módulo registra ok, outro levanta no import."""
    pkg = tmp_path / "fakeroutines"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "ok_one.py").write_text(
        "from orchestrator import register\n"
        "from orchestrator.types import RoutineResult\n"
        "from intelligence.types import Action\n"
        "@register('ok-one')\n"
        "def run(ctx):\n"
        "    return RoutineResult(action=Action.PROCEED_TO_WEB)\n"
    )
    (pkg / "broken.py").write_text("raise RuntimeError('boom')\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    # Limpa qualquer import cache do nome
    for mod in list(sys.modules):
        if mod.startswith("fakeroutines"):
            del sys.modules[mod]

    registry.discover("fakeroutines")
    assert "ok-one" in registry.list_names()
    # módulo broken não derrubou descoberta
