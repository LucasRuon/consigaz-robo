"""Demo: busca web ao vivo com detector de CAPTCHA human-in-the-loop.

Uso:
    uv run python scripts/web_search_demo.py
    uv run python scripts/web_search_demo.py --engine google --query "consigaz robo"
    uv run python scripts/web_search_demo.py --engine ddg --query "RPA python"

O browser fica aberto até você pressionar ENTER. Em CAPTCHA, o script
pausa e faz polling — resolva manualmente na janela do Chromium.
"""

from __future__ import annotations

import argparse
import time
from typing import Any

from config import Settings
from web import close_browser, navigate_to, open_browser

_CAPTCHA_URL_MARKERS = ("/sorry/", "/captcha", "challenge")
_CAPTCHA_IFRAMES = (
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "iframe[src*='challenges.cloudflare']",
)
_ENGINES: dict[str, dict[str, str]] = {
    "google": {
        "url": "https://www.google.com",
        "input": "textarea[name='q'], input[name='q']",
        "results": "div#search h3",
    },
    "ddg": {
        "url": "https://duckduckgo.com/",
        "input": "input[name='q']",
        "results": "article[data-testid='result'] h2",
    },
}


def captcha_visible(page: Any) -> bool:
    if any(m in page.url for m in _CAPTCHA_URL_MARKERS):
        return True
    return any(page.locator(sel).count() > 0 for sel in _CAPTCHA_IFRAMES)


def wait_for_human(page: Any, *, timeout_s: int) -> bool:
    print(f"\n🛑 CAPTCHA detectado: {page.url}")
    print(f"   Vá até a janela do Chromium e resolva. Timeout: {timeout_s}s.\n")
    start = time.monotonic()
    last_log = 0.0
    while time.monotonic() - start < timeout_s:
        if not captcha_visible(page):
            print("✅ CAPTCHA resolvido — continuando.\n")
            return True
        elapsed = int(time.monotonic() - start)
        if elapsed - last_log >= 15:
            print(f"   ⏳ ainda aguardando... ({elapsed}/{timeout_s}s)")
            last_log = elapsed
        time.sleep(3)
    print("❌ Timeout aguardando humano.")
    return False


def dismiss_consent(page: Any) -> None:
    for label in ("Aceitar tudo", "Aceito", "Concordo", "Accept all"):
        btn = page.get_by_role("button", name=label)
        try:
            if btn.first.is_visible(timeout=800):
                btn.first.click()
                print(f"  → consent: cliquei '{label}'")
                return
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo web search com CAPTCHA handler")
    parser.add_argument("--engine", choices=list(_ENGINES), default="ddg")
    parser.add_argument("--query", default="consigaz robô RPA python")
    parser.add_argument("--captcha-timeout", type=int, default=300)
    args = parser.parse_args()

    cfg = _ENGINES[args.engine]
    settings = Settings()

    print(f"▶ engine={args.engine} | query={args.query!r}")
    page = open_browser(settings, selectors=None)
    try:
        navigate_to(page, cfg["url"])
        print(f"  → URL: {page.url}")
        dismiss_consent(page)

        if captcha_visible(page) and not wait_for_human(
            page, timeout_s=args.captcha_timeout
        ):
            return 2

        search = page.locator(cfg["input"]).first
        search.wait_for(timeout=15_000)
        search.fill(args.query)
        search.press("Enter")
        page.wait_for_load_state("domcontentloaded", timeout=20_000)
        time.sleep(2)

        if captcha_visible(page) and not wait_for_human(
            page, timeout_s=args.captcha_timeout
        ):
            return 2

        page.wait_for_selector(cfg["results"], timeout=20_000)
        print(f"\n✅ Busca concluída — URL: {page.url}")
        print(f"   Title: {page.title()}\n")

        for i, h in enumerate(page.locator(cfg["results"]).all()[:5], 1):
            try:
                print(f"  [{i}] {h.inner_text().strip()}")
            except Exception:
                pass

        print(
            "\n⏸  Browser permanece aberto. Pressione ENTER aqui para fechar."
        )
        try:
            input()
        except EOFError:
            time.sleep(60)
    finally:
        close_browser()
    print("Browser fechado. OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
