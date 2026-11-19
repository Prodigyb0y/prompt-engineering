"""Caminhos por versão dos dados. Padrão: v1 (dados/ e resultados/).

PE_VERSAO=v2 aponta para dados/v2/ e resultados/v2/. Os prompts não mudam entre versões
(prompts/ é único); só o conjunto de casos e de resultados muda.
"""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VERSAO = os.environ.get("PE_VERSAO", "v1")
if VERSAO not in {"v1", "v2"}:
    raise SystemExit(f"PE_VERSAO inválida: {VERSAO!r} (use v1 ou v2)")
DADOS = RAIZ / "dados" if VERSAO == "v1" else RAIZ / "dados" / "v2"
RESULTADOS = RAIZ / "resultados" if VERSAO == "v1" else RAIZ / "resultados" / "v2"
DOCS = RAIZ / "docs" if VERSAO == "v1" else RAIZ / "docs" / "v2"
