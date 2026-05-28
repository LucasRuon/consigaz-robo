"""Exceções customizadas do módulo Desktop."""

from __future__ import annotations


class PlatformError(RuntimeError):
    """Falha em operação de plataforma (launch_app, focus_window)."""


class TemplateNotFoundError(RuntimeError):
    """Template não encontrado na tela dentro do timeout."""

    def __init__(self, template_path: str, screenshot_path: str, elapsed: float) -> None:
        super().__init__(
            f"Template não encontrado: {template_path!r} após {elapsed:.1f}s. "
            f"Screenshot salvo em {screenshot_path!r}"
        )
        self.template_path = template_path
        self.screenshot_path = screenshot_path
        self.elapsed = elapsed


class InteractionError(RuntimeError):
    """Falha em interação primitiva de UI (click, type, extract)."""

    def __init__(self, action: str, template_path: str | None = None) -> None:
        detail = f" (template: {template_path!r})" if template_path else ""
        super().__init__(f"Falha na interação {action!r}{detail}")
        self.action = action
        self.template_path = template_path


class UnsupportedPlatformError(RuntimeError):
    """Plataforma não suportada pelo módulo Desktop."""
