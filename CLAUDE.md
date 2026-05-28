# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status do repositório

Projeto **greenfield**. No momento existe apenas o PRD (`prd_automacao_rpa.md`) — não há código, dependências, testes ou scripts de build. Qualquer comando "comum" listado abaixo descreve o estado-alvo definido pelo PRD, não comandos que já funcionam hoje. Antes de afirmar que algo "roda", verifique se os arquivos correspondentes existem.

## Visão geral do produto

Robô RPA híbrido (Desktop + Web) para macOS Apple Silicon, em Python 3.11+. O fluxo padrão (happy path) é:

1. Orquestrador carrega config e credenciais.
2. App Desktop é trazido ao foco via AppleScript / `open -a`.
3. PyAutoGUI + OpenCV (template matching por imagens-âncora) navegam o app local e extraem dados.
4. Camada de dados valida campos estruturados e envia textos livres para uma LLM (OpenAI/Anthropic) para classificação/análise semântica.
5. Playwright abre o navegador, reaproveita sessão persistida e injeta os dados validados em formulários web multi-etapas.
6. Resultado e logs são gravados; dados sensíveis são limpos da memória.

## Arquitetura prevista (do PRD)

A separação modular é uma exigência do PRD, não uma sugestão. Ao criar arquivos, respeite estas fronteiras:

- **Orquestrador (core):** ponto de entrada, carrega `.env`/Keychain, decide qual rotina rodar, gerencia logging estruturado (`.log` ou `.json`).
- **Módulo Desktop:** PyAutoGUI + OpenCV + AppleScript. **Nunca** usa `time.sleep` estático para esperar UI — deve fazer *visual anchoring* (polling de `cv2.matchTemplate` em screenshots) com timeout máximo de 15s. Em falha, salva screenshot na pasta de erros e encerra graciosamente.
- **Módulo Web:** Playwright apenas com seletores DOM robustos (role/text/CSS/XPath). **Proibido** dependência visual no módulo web. Sessões persistidas para evitar relogin.
- **Camada de inteligência:** validação determinística primeiro (Pandas); LLM só para texto não-estruturado. Decisão condicional (aprovado → web, reprovado → exceção no desktop) vive aqui, não nos módulos de UI.
- **Configuração isolada:** seletores visuais (templates de imagem) e seletores web ficam em arquivos dedicados (`config.py` / `selectors.json` / `assets/templates/`). Mudança de layout do sistema-alvo deve ser corrigível sem tocar na lógica.

## Regras invariantes do projeto

Estas vêm dos requisitos não-funcionais e devem ser respeitadas em qualquer mudança:

- **Retry com backoff exponencial** em toda chamada HTTP (web API e LLM).
- **Try/except obrigatório** em toda interação de tela; timeout de 15s antes de abortar com screenshot.
- **Credenciais nunca em código** — sempre via `.env` ou Keychain. Nada de segredos em logs.
- **Nativo ARM64**: ao adicionar dependências, confirme que há wheel para Apple Silicon (especialmente `opencv-python`, `numpy`).
- **Sem coordenadas hardcoded** no módulo desktop — toda posição vem de template matching contra `assets/templates/`.

## Comandos (estado-alvo, ainda não implementados)

Quando o projeto for inicializado, espere algo nesta linha. Verifique a existência antes de executar:

```bash
# setup (a definir — provavelmente uv ou venv + pip)
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# execução
python -m orchestrator               # rotina principal
python -m orchestrator --routine X   # rotina específica

# testes (framework ainda não escolhido — provável pytest)
pytest
pytest tests/test_<modulo>.py::<nome>  # teste único
```

Se nenhum destes arquivos existir ainda, **não invente comandos** — pergunte ao usuário ou proponha a estrutura inicial.

## Convenções para novos arquivos

- Imagens-âncora para OpenCV: `assets/templates/<nome_da_tela>/<elemento>.png`.
- Logs de erro com screenshot: `logs/errors/<timestamp>_<rotina>.png` + `.log`.
- Toda nova rotina de automação deve ser um módulo isolado que recebe dados já validados — nunca chamar LLM ou validar dentro de um módulo de UI.
