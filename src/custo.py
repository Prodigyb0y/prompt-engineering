"""Cálculo de custo a partir de config/precos.json (tokens x preço de tabela)."""
import json
from pathlib import Path

PRECOS = Path(__file__).resolve().parent.parent / "config" / "precos.json"
LIMITE_FAIXA = 100_000


def carregar_precos(caminho=PRECOS) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def custo_usd(tokens_entrada: int, tokens_saida: int, precos: dict) -> float:
    faixa = precos["ate_100k_tokens_de_prompt" if tokens_entrada <= LIMITE_FAIXA else "acima_100k_tokens_de_prompt"]
    return (tokens_entrada * faixa["entrada"] + tokens_saida * faixa["saida"]) / 1_000_000
