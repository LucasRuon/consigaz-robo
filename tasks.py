"""Tasks invoke do projeto consigaz-robo. Cross-platform (macOS + Windows).

Uso:
    inv --list                  lista todas as tasks
    inv setup                   sincroniza dependências (uv sync --extra dev)
    inv test [--only PATH]      roda pytest (opcionalmente só um caminho)
    inv lint                    roda ruff check em src/ e tests/
    inv format                  roda ruff format em src/ e tests/
    inv typecheck               roda mypy em src/
    inv smoke                   roda python -m orchestrator --help em subprocess
    inv clean                   remove caches (.pytest_cache, __pycache__, etc.)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from invoke.context import Context
from invoke.tasks import task

ROOT = Path(__file__).parent
SRC = ROOT / "src"
TESTS = ROOT / "tests"


@task
def setup(c: Context) -> None:
    """Sincroniza dependências runtime + dev via uv."""
    c.run("uv sync --extra dev", pty=False)


@task(help={"only": "Caminho relativo de um arquivo ou diretório de testes"})
def test(c: Context, only: str | None = None) -> None:
    """Roda a suíte pytest. Opcionalmente filtra com --only PATH."""
    cmd = "uv run pytest"
    if only:
        cmd += f" {only}"
    c.run(cmd, pty=False)


@task
def lint(c: Context) -> None:
    """Roda ruff check em src/ e tests/."""
    c.run(f"uv run ruff check {SRC} {TESTS}", pty=False)


@task
def format(c: Context) -> None:  # noqa: A001  # shadow do builtin é intencional na CLI
    """Formata src/ e tests/ via ruff format."""
    c.run(f"uv run ruff format {SRC} {TESTS}", pty=False)


@task
def typecheck(c: Context) -> None:
    """Roda mypy --strict em src/."""
    c.run("uv run mypy", pty=False)


@task
def smoke(c: Context) -> None:
    """Smoke e2e: python -m orchestrator --help deve retornar exit 0."""
    result = subprocess.run(
        [sys.executable, "-m", "orchestrator", "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, end="")
        raise SystemExit(result.returncode)
    if "usage:" not in result.stdout.lower():
        print("[smoke] esperava 'usage:' em stdout", file=sys.stderr)
        raise SystemExit(1)


@task
def clean(c: Context) -> None:
    """Remove caches de ferramentas (pytest, mypy, ruff, __pycache__)."""
    targets = [
        ROOT / ".pytest_cache",
        ROOT / ".mypy_cache",
        ROOT / ".ruff_cache",
        ROOT / "htmlcov",
        ROOT / ".coverage",
    ]
    for target in targets:
        if target.is_dir():
            shutil.rmtree(target)
            print(f"removido {target.relative_to(ROOT)}/")
        elif target.is_file():
            target.unlink()
            print(f"removido {target.relative_to(ROOT)}")
    # __pycache__ em qualquer lugar dentro de src/ ou tests/
    for pycache in [*SRC.rglob("__pycache__"), *TESTS.rglob("__pycache__")]:
        shutil.rmtree(pycache)
        print(f"removido {pycache.relative_to(ROOT)}/")
