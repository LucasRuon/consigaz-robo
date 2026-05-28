"""Testes para `logger.setup` (dual sink: .log humano + .json estruturado)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
import structlog

from logger.setup import get_logger, setup_logging


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    """Garante isolamento: limpa handlers stdlib e reseta structlog entre testes."""
    yield
    root = logging.getLogger()
    for handler in list(root.handlers):
        handler.close()
        root.removeHandler(handler)
    structlog.reset_defaults()


def _find_log_files(log_dir: Path, routine: str) -> tuple[Path, Path]:
    log_files = sorted(log_dir.glob(f"*_{routine}.log"))
    json_files = sorted(log_dir.glob(f"*_{routine}.json"))
    assert len(log_files) == 1, f"esperava 1 .log, achei {log_files}"
    assert len(json_files) == 1, f"esperava 1 .json, achei {json_files}"
    return log_files[0], json_files[0]


def test_cria_arquivos_log_e_json(tmp_path: Path) -> None:
    setup_logging("teste_rotina", log_dir=tmp_path, level="INFO")
    log_path, json_path = _find_log_files(tmp_path, "teste_rotina")
    assert log_path.exists()
    assert json_path.exists()


def test_evento_aparece_em_ambos_arquivos(tmp_path: Path) -> None:
    setup_logging("evt", log_dir=tmp_path, level="INFO")
    log = get_logger("teste")
    log.info("hello_world", numero=42)

    # força flush dos handlers
    for handler in logging.getLogger().handlers:
        handler.flush()

    log_path, json_path = _find_log_files(tmp_path, "evt")

    text_content = log_path.read_text(encoding="utf-8")
    assert "hello_world" in text_content
    assert "42" in text_content

    json_lines = [
        json.loads(line) for line in json_path.read_text(encoding="utf-8").splitlines() if line
    ]
    assert any(
        rec.get("event") == "hello_world" and rec.get("numero") == 42 for rec in json_lines
    )


def test_sanitizacao_aplica_em_ambos_arquivos(tmp_path: Path) -> None:
    """O valor 'segredo123' nunca deve aparecer; só '***'."""
    setup_logging("sec", log_dir=tmp_path, level="INFO")
    log = get_logger("teste")
    log.info("tentativa_login", password="segredo123", usuario="alice")

    for handler in logging.getLogger().handlers:
        handler.flush()

    log_path, json_path = _find_log_files(tmp_path, "sec")

    text_content = log_path.read_text(encoding="utf-8")
    assert "segredo123" not in text_content
    assert "***" in text_content
    assert "alice" in text_content  # campo não sensível preserva

    json_content = json_path.read_text(encoding="utf-8")
    assert "segredo123" not in json_content
    json_lines = [json.loads(line) for line in json_content.splitlines() if line]
    rec = next(r for r in json_lines if r.get("event") == "tentativa_login")
    assert rec["password"] == "***"
    assert rec["usuario"] == "alice"


def test_respeita_log_level(tmp_path: Path) -> None:
    setup_logging("lvl", log_dir=tmp_path, level="WARNING")
    log = get_logger("teste")
    log.info("info_silenciado")
    log.warning("warning_visivel")

    for handler in logging.getLogger().handlers:
        handler.flush()

    log_path, json_path = _find_log_files(tmp_path, "lvl")
    text_content = log_path.read_text(encoding="utf-8")
    json_content = json_path.read_text(encoding="utf-8")

    assert "info_silenciado" not in text_content
    assert "warning_visivel" in text_content
    assert "info_silenciado" not in json_content
    assert "warning_visivel" in json_content


def test_encoding_utf8_nos_dois_arquivos(tmp_path: Path) -> None:
    """Mensagens com acentos devem chegar nos arquivos sem mojibake."""
    setup_logging("acento", log_dir=tmp_path, level="INFO")
    log = get_logger("teste")
    log.info("operação_concluída", detalhe="análise não pôde ser executada")

    for handler in logging.getLogger().handlers:
        handler.flush()

    log_path, json_path = _find_log_files(tmp_path, "acento")
    text_content = log_path.read_text(encoding="utf-8")
    json_content = json_path.read_text(encoding="utf-8")

    assert "operação_concluída" in text_content
    json_lines = [json.loads(line) for line in json_content.splitlines() if line]
    rec = next(r for r in json_lines if "operação_concluída" in r.get("event", ""))
    assert rec["detalhe"] == "análise não pôde ser executada"


def test_cria_log_dir_se_nao_existir(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "nested" / "dir"
    assert not nested.exists()
    setup_logging("mkd", log_dir=nested, level="INFO")
    assert nested.is_dir()


def test_get_logger_retorna_bound_logger() -> None:
    setup_logging("gl", log_dir=Path("/tmp"), level="INFO")
    log = get_logger("modulo.x")
    assert hasattr(log, "info")
    assert hasattr(log, "bind")
