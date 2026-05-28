"""Testes do processor structlog de sanitização de chaves sensíveis."""
from __future__ import annotations

from logger.processors import MASK, make_sanitizer


def test_chave_exata_mascarada() -> None:
    proc = make_sanitizer()
    result = proc(None, "info", {"password": "abc123"})
    assert result == {"password": MASK}


def test_case_insensitive() -> None:
    proc = make_sanitizer()
    result = proc(None, "info", {"Password": "x", "PASSWORD": "y", "PaSsWoRd": "z"})
    assert result == {"Password": MASK, "PASSWORD": MASK, "PaSsWoRd": MASK}


def test_substring_match() -> None:
    proc = make_sanitizer()
    result = proc(None, "info", {"openai_api_key": "sk-123"})
    assert result == {"openai_api_key": MASK}


def test_chave_sem_match_preservada() -> None:
    proc = make_sanitizer()
    result = proc(None, "info", {"username": "alice"})
    assert result == {"username": "alice"}


def test_mistura_chaves() -> None:
    proc = make_sanitizer()
    result = proc(None, "info", {"username": "alice", "password": "x", "email": "a@b.c"})
    assert result == {"username": "alice", "password": MASK, "email": "a@b.c"}


def test_sensitive_keys_customizado() -> None:
    proc = make_sanitizer(frozenset({"foo"}))
    result = proc(None, "info", {"foo": "bar", "password": "x"})
    assert result == {"foo": MASK, "password": "x"}


def test_dict_aninhado_nao_processado() -> None:
    proc = make_sanitizer()
    nested = {"password": "abc"}
    result = proc(None, "info", {"payload": nested})
    assert result == {"payload": {"password": "abc"}}


def test_chaves_default_cobrem_documentos_br() -> None:
    proc = make_sanitizer()
    result = proc(None, "info", {"cpf": "111", "cnpj": "222", "rg": "333"})
    assert result == {"cpf": MASK, "cnpj": MASK, "rg": MASK}
