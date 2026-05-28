"""Carregamento e acesso ao config/selectors.json."""

from __future__ import annotations

import json
from pathlib import Path

from web.exceptions import SelectorLoadError, SelectorNotFoundError

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_PATH = _PROJECT_ROOT / "config" / "selectors.json"


def load_selectors(path: str | Path | None = None) -> dict[str, dict[str, str]]:
    """Carrega selectors.json; lança FileNotFoundError ou SelectorLoadError."""
    resolved = Path(path) if path is not None else _DEFAULT_PATH
    if not resolved.exists():
        raise FileNotFoundError(f"Arquivo de seletores não encontrado: {resolved}")
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SelectorLoadError(str(resolved), str(exc)) from exc
    if not isinstance(data, dict):
        raise SelectorLoadError(str(resolved), "raiz do JSON deve ser um objeto")
    return data


def get_selector(
    selectors: dict[str, dict[str, str]],
    page: str,
    key: str,
) -> str:
    """Retorna seletor; lança SelectorNotFoundError se página ou chave ausente."""
    page_map = selectors.get(page)
    if page_map is None:
        raise SelectorNotFoundError(page, key)
    value = page_map.get(key)
    if value is None:
        raise SelectorNotFoundError(page, key)
    return value
