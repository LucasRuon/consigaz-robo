# Templates — `pilot-smoke`

Esta pasta contém os templates de imagem usados pela camada Desktop (OpenCV
template matching) para a rotina-piloto.

## Estrutura

```
pilot-smoke/
├── darwin/                 # capturas em macOS (Calculator.app)
│   ├── window_titlebar.png
│   ├── btn_2.png
│   ├── btn_3.png
│   ├── btn_plus.png
│   └── btn_equals.png
└── win32/                  # placeholder; capturar quando houver máquina Windows
    └── .gitkeep
```

## ⚠️ Placeholders em `darwin/`

Os PNGs atuais em `darwin/` são **placeholders 1×1 cinza**, criados apenas para
satisfazer testes de existência/formato. Eles **não funcionam** para template
matching real.

Antes de rodar o E2E (`RUN_E2E_PILOT_SMOKE=1`), substitua cada arquivo por uma
captura real:

1. Abra a Calculadora nativa (`open -a Calculator`) em tema claro, zoom nativo
   do display.
2. Tire um screenshot recortado em cada elemento (≤ 100 KB cada):
   - `window_titlebar.png`: trecho fixo da barra de título da janela (âncora
     de "Calculadora carregada").
   - `btn_2.png`, `btn_3.png`, `btn_plus.png`, `btn_equals.png`: cada botão
     em seu estado padrão (não-pressionado).
3. Threshold default de `wait_for_template` é 0.8 — capture com nitidez e sem
   sombras dinâmicas (não use modo escuro, não use zoom dinâmico do macOS).

## Por que arquivos no repo

Templates são parte do contrato visual da rotina, versionados junto ao código
(invariante M0). Mudança de layout do app-alvo é resolvida atualizando estes
PNGs, sem tocar em código.
