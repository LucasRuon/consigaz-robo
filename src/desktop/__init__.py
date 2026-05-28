"""Módulo Desktop: abstração de plataforma, ancoragem visual e interações primitivas."""

from desktop.exceptions import (
    InteractionError,
    PlatformError,
    TemplateNotFoundError,
    UnsupportedPlatformError,
)
from desktop.interactions import (
    clear_field,
    click_at_template,
    extract_via_clipboard,
    type_text,
)
from desktop.platform.adapter import PlatformAdapter, get_platform_adapter
from desktop.vision import wait_for_template

__all__ = [
    "InteractionError",
    "PlatformAdapter",
    "PlatformError",
    "TemplateNotFoundError",
    "UnsupportedPlatformError",
    "clear_field",
    "click_at_template",
    "extract_via_clipboard",
    "get_platform_adapter",
    "type_text",
    "wait_for_template",
]
