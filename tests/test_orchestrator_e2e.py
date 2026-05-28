"""Teste e2e: `python -m orchestrator` em subprocess real."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "orchestrator", *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )


def test_help_imprime_usage_exit_zero() -> None:
    result = _run(["--help"])
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_sem_args_imprime_usage_exit_zero() -> None:
    result = _run([])
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
