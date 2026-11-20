"""Caminhos por versão dos dados. Padrão: v1 (dados/extracao/v1 e resultados/extracao/v1).

PE_VERSAO=v2 aponta para dados/extracao/v2/ e resultados/extracao/v2/. Os prompts não mudam entre versões
(prompts/extracao/ é único); só o conjunto de casos e de resultados muda.
"""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VERSAO = os.environ.get("PE_VERSAO", "v1")
if VERSAO not in {"v1", "v2"}:
    raise SystemExit(f"PE_VERSAO inválida: {VERSAO!r} (use v1 ou v2)")
DADOS = RAIZ / "dados" / "extracao" / VERSAO
RESULTADOS = RAIZ / "resultados" / "extracao" / VERSAO
DOCS = RAIZ / "docs"
