"""Verifica presença e formato dos templates da rotina pilot-smoke."""

from __future__ import annotations

from pathlib import Path

_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_BASE = Path("assets/templates/pilot-smoke")
_DARWIN_TEMPLATES = (
    "window_titlebar",
    "btn_2",
    "btn_3",
    "btn_plus",
    "btn_equals",
)


def test_darwin_templates_exist_and_are_png() -> None:
    darwin = _BASE / "darwin"
    for name in _DARWIN_TEMPLATES:
        path = darwin / f"{name}.png"
        assert path.exists(), f"template ausente: {path}"
        assert path.stat().st_size < 100_000, f"template > 100 KB: {path}"
        with path.open("rb") as fh:
            assert fh.read(8) == _PNG_SIG, f"não é PNG válido: {path}"


def test_win32_has_gitkeep_placeholder() -> None:
    assert (_BASE / "win32" / ".gitkeep").exists()
