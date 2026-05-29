"""Teste E2E da rotina `pilot-smoke` (gateado por env vars).

Ativação (rodar localmente em macOS com Calculadora real e API key válida):
    export RUN_E2E_PILOT_SMOKE=1
    export OPENAI_API_KEY=sk-...
    pytest -m e2e tests/test_routines/test_pilot_smoke_e2e.py -v

Em CI ou sem essas vars os 3 testes são `skipped`, nunca `failed`.
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_RUN_E2E = os.getenv("RUN_E2E_PILOT_SMOKE") == "1"
_HAS_API_KEY = bool(os.getenv("OPENAI_API_KEY"))
_IS_MAC = sys.platform == "darwin"

_REASON_NOT_E2E = "E2E desativado (defina RUN_E2E_PILOT_SMOKE=1, OPENAI_API_KEY, e rode em darwin)"


def _latest_log_summary() -> dict[str, object]:
    """Lê o último .json em logs/ e devolve o evento execution_summary mais recente."""
    log_files = sorted(glob.glob("logs/*.json"))
    assert log_files, "nenhum log .json encontrado em logs/"
    latest = Path(log_files[-1])
    summaries: list[dict[str, object]] = []
    for line in latest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == "execution_summary":
            summaries.append(event)
    assert summaries, f"nenhum execution_summary em {latest}"
    return summaries[-1]


@pytest.mark.e2e
@pytest.mark.skipif(
    not (_RUN_E2E and _HAS_API_KEY and _IS_MAC),
    reason=_REASON_NOT_E2E,
)
def test_full_pipeline_macos() -> None:
    """Executa a rotina completa em macOS e verifica exit 0 + summary saudável."""
    proc = subprocess.run(
        [sys.executable, "-m", "orchestrator", "--routine", "pilot-smoke"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    summary = _latest_log_summary()
    assert summary.get("action") == "proceed_to_web"
    assert int(summary.get("tokens_in", 0)) > 0
    assert "error_type" not in summary


@pytest.mark.e2e
@pytest.mark.skipif(
    not (_RUN_E2E and _HAS_API_KEY and _IS_MAC),
    reason=_REASON_NOT_E2E,
)
def test_dry_run_does_not_submit() -> None:
    """Em --dry-run o submit web é pulado; evidence contém dry_run, não web_final_url."""
    proc = subprocess.run(
        [sys.executable, "-m", "orchestrator", "--routine", "pilot-smoke", "--dry-run"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    summary = _latest_log_summary()
    keys = summary.get("evidence_keys") or []
    assert "dry_run" in keys
    assert "web_final_url" not in keys


@pytest.mark.e2e
@pytest.mark.skipif(
    not (_RUN_E2E and _IS_MAC),
    reason=_REASON_NOT_E2E,
)
def test_invalid_api_key_returns_exit_3() -> None:
    """API key inválida → exit code 3 (LLM error) + error_type no summary."""
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = "sk-invalid-key-for-testing"
    proc = subprocess.run(
        [sys.executable, "-m", "orchestrator", "--routine", "pilot-smoke"],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert proc.returncode == 3, f"esperado exit 3, obtido {proc.returncode}"
    summary = _latest_log_summary()
    assert "error_type" in summary
