"""Boot do orquestrador: compõe plataforma, config, logger e excepthook."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config import Settings
from logger.screenshot_hook import install_excepthook
from logger.setup import get_logger, setup_logging
from platform_info import Platform, current_platform


@dataclass(frozen=True)
class BootContext:
    """Estado inicializado após `boot()`. Imutável; passado adiante pelas rotinas."""

    platform: Platform
    settings: Settings
    routine: str
    log_dir: Path


def boot(
    routine: str = "default",
    log_dir: Path | None = None,
    errors_dir: Path | None = None,
) -> BootContext:
    """Sequência de inicialização do robô. Retorna `BootContext` ou lança em falha."""
    platform = current_platform()
    settings = Settings()

    effective_log_dir = log_dir or settings.log_dir
    effective_errors_dir = errors_dir or (effective_log_dir / "errors")

    setup_logging(
        routine=routine,
        log_dir=effective_log_dir,
        level=settings.log_level,
        sensitive_keys=settings.sensitive_keys,
    )
    install_excepthook(routine=routine, errors_dir=effective_errors_dir)

    log = get_logger(__name__)
    log.info(
        "boot_concluido",
        plataforma=platform.value,
        profile=settings.profile,
        log_level=settings.log_level,
        routine=routine,
    )

    return BootContext(
        platform=platform,
        settings=settings,
        routine=routine,
        log_dir=effective_log_dir,
    )
