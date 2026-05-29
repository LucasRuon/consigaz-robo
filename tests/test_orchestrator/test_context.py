"""Testes de `orchestrator.context.RoutineContext`."""

from __future__ import annotations

import dataclasses
from datetime import UTC
from pathlib import Path

import pytest

from config import Settings
from orchestrator.boot import BootContext
from orchestrator.context import RoutineContext
from platform_info import Platform


@pytest.fixture
def boot_ctx(monkeypatch: pytest.MonkeyPatch) -> BootContext:
    monkeypatch.setattr("keyring.get_password", lambda service, key: None)
    for var in ("OPENAI_API_KEY", "DESKTOP_APP_PASSWORD", "WEB_PLATFORM_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    return BootContext(
        platform=Platform.DARWIN,
        settings=Settings(_env_file=None),  # type: ignore[call-arg]
        routine="boot_default",
        log_dir=Path("logs"),
    )


def test_from_boot_aplica_routine_name(boot_ctx: BootContext) -> None:
    ctx = RoutineContext.from_boot(boot_ctx, dry_run=False, routine_name="minha")
    assert ctx.routine_name == "minha"


def test_from_boot_default_usa_boot_routine(boot_ctx: BootContext) -> None:
    ctx = RoutineContext.from_boot(boot_ctx, dry_run=True)
    assert ctx.routine_name == "boot_default"
    assert ctx.dry_run is True


def test_context_eh_frozen(boot_ctx: BootContext) -> None:
    ctx = RoutineContext.from_boot(boot_ctx, dry_run=False)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.dry_run = True  # type: ignore[misc]


def test_started_at_tz_aware_utc(boot_ctx: BootContext) -> None:
    ctx = RoutineContext.from_boot(boot_ctx, dry_run=False)
    assert ctx.started_at.tzinfo is not None
    assert ctx.started_at.utcoffset() == UTC.utcoffset(ctx.started_at)


def test_logger_bound_com_routine(boot_ctx: BootContext) -> None:
    ctx = RoutineContext.from_boot(boot_ctx, dry_run=False, routine_name="x")
    # structlog BoundLogger expõe `_context` com os binds aplicados.
    assert ctx.logger._context.get("routine") == "x"  # type: ignore[attr-defined]
