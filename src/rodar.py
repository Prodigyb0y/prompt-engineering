"""Executa técnicas x casos x repetições e grava cada resposta bruta.

  python src/rodar.py --piloto     # 5 casos (sorteio seed 42), T1 e T4, 1 repetição
  python src/rodar.py --completo   # 4 técnicas x 50 casos x 3 repetições
  PE_VERSAO=v2 python src/rodar.py --iteracao   # só o T4 com o prompt v2, 50 casos x 3 repetições (150 chamadas)
  PE_VERSAO=v3 python src/rodar.py --validacao  # T4 v1 e T4 v2 em 20 casos NOVOS (congelados), 3 repetições (120 chamadas)

Cada resposta vai para resultados/brutos/<T>_<caso>_r<rep>.json (a pasta é versionada no Git, para o resultado poder ser conferido).
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

import caminhos

RAIZ = caminhos.RAIZ
BRUTOS = caminhos.RESULTADOS / "brutos"
# folga para o raciocínio oculto (conta como saída); o teto de gasto continua valendo
MAX_TOKENS = {"T1": 2000, "T2": 2000, "T3": 3000, "T4": 2000}


def selecionar(modo, casos):
    if modo == "piloto":
        ids = sorted(random.Random(42).sample([c["id"] for c in casos], 5))
        return [c for c in casos if c["id"] in ids], ["T1", "T4"], 1
    if modo == "iteracao":
        return casos, ["T4"], 3
    return casos, ["T1", "T2", "T3", "T4"], 3


def executar_validacao(cliente, casos, gabarito, pasta=None):
    """T4 v1 e T4 v2 nos casos novos (v3). Cada versão grava em sua própria pasta: brutos/v1 e brutos/v2."""
    pasta = pasta or caminhos.RESULTADOS / "brutos"
    total_feitas = total_novas = 0
    for versao in ("v1", "v2"):
        for tid, reps in [("T4", 3)]:
            f, n = _rodar(cliente, casos, gabarito, pasta / versao, [tid], reps, versao)
            total_feitas += f
            total_novas += n
    return total_feitas, total_novas


def _rodar(cliente, lista, gabarito, pasta, tecnicas, reps, versao):
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
                print(f"[{tid} {versao} {caso['id']} r{rep}] ok={aval['caso_correto']} custo=US$ {r['custo_usd']:.6f} gasto={cliente.controle.gasto:.6f}", flush=True)
    return feitas, novas


def executar(modo, cliente, casos, gabarito, pasta=BRUTOS, versao="v1"):
    lista, tecnicas, reps = selecionar(modo, casos)
    return _rodar(cliente, lista, gabarito, pasta, tecnicas, reps, versao)


def main_validacao():
    """Validação do T4 v2 em casos novos. Usa o livro-caixa das rodadas novas (US$ 0,60 e US$ 1,00 no total)."""
    import experimentos as ex
    if caminhos.VERSAO != "v3":
        sys.exit("A validação usa os casos novos: rode com PE_VERSAO=v3.")
    import validar_dados_v3
    atual = validar_dados_v3.hashes()
    esperado = {l.split()[1]: l.split()[0] for l in (caminhos.DADOS / "CONGELADO.sha256").read_text(encoding="utf-8").splitlines()}
    if atual != esperado:
        sys.exit("Os dados v3 mudaram depois do congelamento (CONGELADO.sha256). Não rode a validação.")
    casos = json.loads((caminhos.DADOS / "casos_teste.json").read_text(encoding="utf-8"))
    gab = json.loads((caminhos.DADOS / "gabarito.json").read_text(encoding="utf-8"))
    ctl = ex.ControleBiblioteca()
    cli = ClienteAnthropic(ctl)
    try:
        feitas, novas = executar_validacao(cli, casos, gab)
    except TetoExcedido as e:
        print("PARADO pelo teto de gasto:", e)
        sys.exit(2)
    print(f"[dados v3] validação: {novas} chamadas novas, {feitas} já existiam. Gasto novo acumulado: US$ {ctl.gasto:.6f} de US$ {ex.TETO_RODADAS_USD:.2f}")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--piloto", action="store_true")
    g.add_argument("--completo", action="store_true")
    g.add_argument("--iteracao", action="store_true")
    g.add_argument("--validacao", action="store_true")
    args = ap.parse_args()
    modo = "piloto" if args.piloto else "iteracao" if args.iteracao else "validacao" if args.validacao else "completo"
    if modo == "validacao":
        return main_validacao()
    if modo == "iteracao" and caminhos.VERSAO != "v2":
        sys.exit("A iteração do prompt é avaliada nos dados v2: rode com PE_VERSAO=v2.")
    casos = json.loads((caminhos.DADOS / "casos_teste.json").read_text(encoding="utf-8"))
    gab = json.loads((caminhos.DADOS / "gabarito.json").read_text(encoding="utf-8"))
    ctl = ControleCusto()
    cli = ClienteAnthropic(ctl)
    try:
        if modo == "iteracao":
            feitas, novas = executar(modo, cli, casos, gab, caminhos.RESULTADOS / "iteracao" / "brutos", versao="v2")
        else:
            feitas, novas = executar(modo, cli, casos, gab, BRUTOS / modo if modo == "piloto" else BRUTOS)
    except TetoExcedido as e:
        print("PARADO pelo teto de gasto:", e)
        sys.exit(2)
    print(f"[dados {caminhos.VERSAO}] {modo}: {novas} chamadas novas, {feitas} já existiam. Gasto acumulado: US$ {ctl.gasto:.6f} de US$ {ctl.teto:.2f}")


if __name__ == "__main__":
    main()
