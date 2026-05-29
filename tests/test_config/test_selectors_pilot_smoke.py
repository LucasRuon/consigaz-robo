"""Testes do bloco `pilot_smoke` em `config/selectors.json`."""

from __future__ import annotations

from web.selectors import load_selectors


def test_pilot_smoke_block_exists() -> None:
    selectors = load_selectors()
    assert "pilot_smoke" in selectors


def test_pilot_smoke_has_all_expected_keys() -> None:
    selectors = load_selectors()
    block = selectors["pilot_smoke"]
    for key in (
        "_session_sentinel",
        "custname",
        "custtel",
        "custemail",
        "comments",
        "submit",
    ):
        assert key in block, f"chave esperada ausente: {key}"
        assert block[key], f"seletor vazio para {key}"
