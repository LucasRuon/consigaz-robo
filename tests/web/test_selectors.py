"""Testes unitários para web/selectors.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from web.exceptions import SelectorLoadError, SelectorNotFoundError
from web.selectors import _DEFAULT_PATH, get_selector, load_selectors


@pytest.fixture()
def valid_json(tmp_path: Path) -> Path:
    data = {
        "login": {
            "username": "input[name='username']",
            "password": "input[name='password']",
            "_session_sentinel": "#app-main",
        },
        "cadastro": {
            "nome": "#nome",
        },
    }
    p = tmp_path / "selectors.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


class TestLoadSelectors:
    def test_load_ok(self, valid_json: Path) -> None:
        result = load_selectors(valid_json)
        assert result["login"]["username"] == "input[name='username']"

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="nao_existe"):
            load_selectors(tmp_path / "nao_existe.json")

    def test_malformed_json(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{broken", encoding="utf-8")
        with pytest.raises(SelectorLoadError) as exc_info:
            load_selectors(p)
        assert str(p) in exc_info.value.path

    def test_non_dict_root(self, tmp_path: Path) -> None:
        p = tmp_path / "array.json"
        p.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(SelectorLoadError):
            load_selectors(p)

    def test_default_path_points_to_config(self) -> None:
        assert _DEFAULT_PATH.name == "selectors.json"
        assert _DEFAULT_PATH.parent.name == "config"

    def test_default_path_resolves_existing_file(self) -> None:
        assert _DEFAULT_PATH.exists(), "config/selectors.json deve existir"

    def test_load_without_argument_uses_default(self) -> None:
        result = load_selectors()
        assert isinstance(result, dict)
        assert "login" in result

    def test_path_as_string(self, valid_json: Path) -> None:
        result = load_selectors(str(valid_json))
        assert "login" in result


class TestGetSelector:
    @pytest.fixture()
    def selectors(self, valid_json: Path) -> dict[str, dict[str, str]]:
        return load_selectors(valid_json)

    def test_returns_correct_selector(
        self, selectors: dict[str, dict[str, str]]
    ) -> None:
        assert get_selector(selectors, "login", "username") == "input[name='username']"

    def test_page_missing(self, selectors: dict[str, dict[str, str]]) -> None:
        with pytest.raises(SelectorNotFoundError) as exc_info:
            get_selector(selectors, "pagina_inexistente", "campo")
        assert exc_info.value.page == "pagina_inexistente"
        assert exc_info.value.key == "campo"

    def test_key_missing(self, selectors: dict[str, dict[str, str]]) -> None:
        with pytest.raises(SelectorNotFoundError) as exc_info:
            get_selector(selectors, "login", "chave_inexistente")
        assert exc_info.value.page == "login"
        assert exc_info.value.key == "chave_inexistente"

    def test_metadata_key_accessible(
        self, selectors: dict[str, dict[str, str]]
    ) -> None:
        sentinel = get_selector(selectors, "login", "_session_sentinel")
        assert sentinel == "#app-main"
