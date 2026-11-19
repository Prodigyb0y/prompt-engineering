"""Executa técnicas x casos x repetições e grava cada resposta bruta.

  python src/rodar.py --piloto     # 5 casos (sorteio seed 42), T1 e T4, 1 repetição
  python src/rodar.py --completo   # 4 técnicas x 50 casos x 3 repetições

Cada resposta vai para resultados/brutos/<T>_<caso>_r<rep>.json (pasta fora do Git).
Roda de forma retomável: arquivo que já existe é pulado. Para no primeiro erro que
sobrar depois dos retries, ou quando o teto de gasto bloquearia a próxima chamada.
"""
import argparse
import json
import random
import sys
from pathlib import Path

import prompts_lib
import validador
from cliente import ESFORCO, MODELO, ClienteAnthropic, ControleCusto, TetoExcedido

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "resultados" / "brutos"
# folga para o raciocínio oculto (conta como saída); o teto de gasto continua valendo
MAX_TOKENS = {"T1": 2000, "T2": 2000, "T3": 3000, "T4": 2000}


def selecionar(modo, casos):
    if modo == "piloto":
        ids = sorted(random.Random(42).sample([c["id"] for c in casos], 5))
        return [c for c in casos if c["id"] in ids], ["T1", "T4"], 1
    return casos, ["T1", "T2", "T3", "T4"], 3


def executar(modo, cliente, casos, gabarito, pasta=BRUTOS, versao="v1"):
    lista, tecnicas, reps = selecionar(modo, casos)
    pasta.mkdir(parents=True, exist_ok=True)
    feitas = novas = 0
    for tid in tecnicas:
        prompt = prompts_lib.carregar(tid, versao)
        for caso in sorted(lista, key=lambda c: c["id"]):
            for rep in range(1, reps + 1):
                arq = pasta / f"{tid}_{caso['id']}_r{rep}.json"
                if arq.exists():
                    feitas += 1
                    continue
                system, user = prompts_lib.montar(prompt, caso["texto"])
                r = cliente.chamar(system, user, MAX_TOKENS[tid])
                aval = validador.avaliar(r["texto"], gabarito[caso["id"]], tid)
                arq.write_text(json.dumps({
                    "tecnica": tid, "prompt_versao": prompt["versao"], "prompt_hash12": prompt["hash12"],
                    "caso": caso["id"], "tipo": caso["tipo"], "repeticao": rep, "resposta": r["texto"],
                    "tokens_entrada": r["tokens_entrada"], "tokens_saida": r["tokens_saida"],
                    "custo_usd": r["custo_usd"], "latencia_s": r["latencia_s"], "tentativas": r["tentativas"],
                    "stop_reason": r.get("stop_reason"), "esforco": ESFORCO, "modelo": MODELO,
                    "avaliacao": aval}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                novas += 1
    return feitas, novas


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--piloto", action="store_true")
    g.add_argument("--completo", action="store_true")
    modo = "piloto" if ap.parse_args().piloto else "completo"
    casos = json.loads((RAIZ / "dados" / "casos_teste.json").read_text(encoding="utf-8"))
    gab = json.loads((RAIZ / "dados" / "gabarito.json").read_text(encoding="utf-8"))
    ctl = ControleCusto()
    cli = ClienteAnthropic(ctl)
    try:
        feitas, novas = executar(modo, cli, casos, gab, BRUTOS / modo if modo == "piloto" else BRUTOS)
    except TetoExcedido as e:
        print("PARADO pelo teto de gasto:", e)
        sys.exit(2)
    print(f"{modo}: {novas} chamadas novas, {feitas} já existiam. Gasto acumulado: US$ {ctl.gasto:.6f} de US$ {ctl.teto:.2f}")


if __name__ == "__main__":
    main()
