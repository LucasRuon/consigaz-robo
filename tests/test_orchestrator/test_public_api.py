"""Smoke test do `orchestrator.__init__` (T10)."""

from __future__ import annotations


def test_imports_publicos() -> None:
    import orchestrator

    # Smoke: cada nome de __all__ é resolvível como atributo do pacote.
    for nome in orchestrator.__all__:
        assert hasattr(orchestrator, nome), f"falta atributo {nome}"

    nomes = {
        "BootContext", "Routine", "RoutineContext", "RoutineNameError",
        "RoutineRegistryError", "RoutineResult", "UnknownRoutineError",
        "boot", "discover", "dispatch", "get", "list_names", "register",
    }
    assert set(orchestrator.__all__) == nomes


def test_routines_package_importavel() -> None:
    import routines

    assert routines is not None
