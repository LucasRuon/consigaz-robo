"""Pacote raiz das rotinas reais (M5+).

Cada rotina é um módulo aqui dentro com uma função decorada por
`@orchestrator.register("nome")`. O orquestrador chama
`orchestrator.registry.discover("routines")` no startup, que importa todos
os submódulos deste pacote e dispara os decoradores.

Limitação aceita: somente o primeiro nível (não há walk em subpacotes).
Se necessário em M5+, trocar `iter_modules` por `walk_packages`.
"""

from __future__ import annotations
