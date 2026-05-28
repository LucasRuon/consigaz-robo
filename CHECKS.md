# Pre-merge Checklist Cross-Platform

Antes de marcar uma feature ou milestone como "done", rodar este checklist em
**macOS arm64** E **Windows 10/11 x86_64**. O M0 só vira "verified
cross-platform" quando as duas seções estiverem totalmente marcadas.

Convenções:

- `[x]` — validado e passou
- `[ ]` — pendente / não rodado
- `[~]` — validado indiretamente (por exemplo, via teste automatizado quando a
  validação real exige permissão de SO)

---

## macOS

Pré-requisito: Python 3.11+ instalado e `uv` no PATH (`export PATH="$HOME/.local/bin:$PATH"`).

- [x] `uv sync --extra dev` completa sem erro
- [x] `uv run inv test` retorna exit 0 (todos os testes passam — 72/72)
- [x] `uv run inv lint` retorna exit 0 (ruff: "All checks passed!")
- [x] `uv run inv typecheck` retorna exit 0 (mypy --strict: "no issues found in 13 source files")
- [x] `uv run python -m orchestrator --help` imprime usage e retorna exit 0
- [x] `uv run inv smoke` valida o subprocess `--help` end-to-end
- [x] Logs em `logs/` aparecem como `<timestamp>_<routine>.log` E `.json` ao rodar uma rotina de teste
      (validado em `/tmp/checks_t16/logs/`: gerados `20260528T183437Z_validacao_t16.log` e `.json`)
- [~] Screenshot em `logs/errors/` aparece quando uma exceção é forçada
      (validado via teste automatizado `tests/test_logger_screenshot_hook.py` — 6 testes passam com FakeScreenshot.
      Validação em condição real exige permissão **Gravação de Tela** concedida ao terminal/iTerm
      e disparo de uma exceção não-tratada num processo descartável.)
- [~] Permissão Acessibilidade concedida ao terminal/iTerm (para pyautogui)
      (Ainda não exercitado por código nesta milestone — pyautogui entra em uso a partir de M2.
      Marcar `[x]` quando a primeira rotina desktop rodar e a permissão for confirmada.)
- [x] Encoding UTF-8 sem mojibake nos logs com acentos
      (`operação_concluída` aparece literal no `.log` e como `ção` no `.json` — ambos corretos;
      sem mojibake. Chave sensível `password` foi mascarada como `***` corretamente.)

**Última validação:** 2026-05-28 — Darwin arm64 (Apple Silicon), Python 3.14.4, executada por Claude (Opus 4.7) em sessão T16. 9 de 10 itens marcados como `[x]`; 2 ficam como `[~]` por dependerem de permissão de SO / código que ainda não roda em M0.

---

## Windows

Pré-requisito: Python 3.11+ no PATH, `uv` instalado (`winget install --id=astral-sh.uv` ou via `pip install uv`).

- [ ] `uv sync --extra dev` completa sem erro
- [ ] `uv run inv test` retorna exit 0 (todos os testes passam)
- [ ] `uv run inv lint` retorna exit 0 (ruff)
- [ ] `uv run inv typecheck` retorna exit 0 (mypy --strict)
- [ ] `uv run python -m orchestrator --help` imprime usage e retorna exit 0
- [ ] `uv run inv smoke` valida o subprocess `--help` end-to-end
- [ ] Logs em `logs\` aparecem como `<timestamp>_<routine>.log` E `.json` ao rodar uma rotina de teste
- [ ] Screenshot em `logs\errors\` aparece quando uma exceção é forçada
- [ ] Caminhos com backslash (`\`) funcionam (regressão clássica de Path handling)
- [ ] Encoding UTF-8 sem mojibake nos logs com acentos (executar `chcp 65001` no console antes se necessário)
- [ ] UAC não bloqueia execução normal (rodar sem "Run as Administrator")

**Última validação:** _pendente_ — sem máquina Windows disponível em 2026-05-28. Quando rodar, registrar aqui: data, versão Windows (`winver`), Python (`python --version`), e quem validou.

---

## Como rodar este checklist

```bash
# em macOS / Linux
cd /caminho/para/consigaz-robo
export PATH="$HOME/.local/bin:$PATH"
uv sync --extra dev
uv run inv test
uv run inv lint
uv run inv typecheck
uv run python -m orchestrator --help
uv run inv smoke
```

```powershell
# em Windows (PowerShell)
cd C:\caminho\para\consigaz-robo
uv sync --extra dev
uv run inv test
uv run inv lint
uv run inv typecheck
uv run python -m orchestrator --help
uv run inv smoke
```

### Validação manual dos logs (ambos SOs)

Roda um boot rápido num diretório descartável e verifica:

1. Que dois arquivos foram criados — um `.log` e um `.json` — com prefixo de timestamp ISO compacto.
2. Que acentos PT-BR aparecem corretos (sem `Ã§`, `Ã£`, etc.).
3. Que chaves sensíveis (`password`, `passwd`, `secret`, `token`, `api_key`, `authorization`) aparecem como `***` em vez do valor real.

```bash
uv run python -c "
from orchestrator.boot import boot
import pathlib, structlog
boot('checklist', log_dir=pathlib.Path('./_check_logs'), errors_dir=pathlib.Path('./_check_errors'))
log = structlog.stdlib.get_logger('test')
log.info('teste', mensagem='operação_concluída', password='nao-deve-aparecer')
"
```

Esperado: `password=***` (não o valor literal) nos dois arquivos.
