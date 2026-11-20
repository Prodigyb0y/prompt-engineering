"""Roda o piloto e as rodadas completas de P2 a P5 (E3, E4, E5 e P4). Precisa de ANTHROPIC_API_KEY.

  python src/rodar_biblioteca.py --piloto                 # 5 chamadas por prompt novo (20 chamadas)
  python src/rodar_biblioteca.py --completo               # E3, E4, E5 e P4: 20 casos x 3 repetições por variante
  python src/rodar_biblioteca.py --completo --so E5       # só um experimento (E3, E4, E5 ou P4)

A chave vem só de ANTHROPIC_API_KEY (variável de ambiente ou arquivo .env local, nunca versionado).
A rodada completa só começa se o piloto existir e a projeção de custo couber nos US$ 0,60 das rodadas novas.
"""
import argparse
import json
import sys

import experimentos as ex
from cliente import ClienteAnthropic


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--piloto", action="store_true")
    g.add_argument("--completo", action="store_true")
    ap.add_argument("--so", choices=["E3", "E4", "E5", "P4"])
    args = ap.parse_args()

    ctl = ex.ControleBiblioteca()
    cli = ClienteAnthropic(ctl)
    if args.piloto:
        r = ex.executar_piloto(cli)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        print(f"\nGasto do piloto: US$ {r['gasto_piloto_usd']:.6f}. Gasto novo acumulado: US$ {ctl.gasto:.6f} de US$ {ex.TETO_RODADAS_USD:.2f}.")
        return

    arq = ex.PILOTO / "piloto.json"
    if not arq.exists():
        sys.exit("Rode o piloto antes: python src/rodar_biblioteca.py --piloto")
    proj = json.loads(arq.read_text(encoding="utf-8")).get("projecao_rodada_completa_usd")
    if proj is None:
        sys.exit("O piloto não terminou sem erro; veja resultados/biblioteca/piloto/piloto.json antes de seguir.")
    if ctl.gasto + proj > ex.TETO_RODADAS_USD:
        sys.exit(f"Projeção da rodada completa (US$ {proj:.4f}) mais o gasto atual (US$ {ctl.gasto:.4f}) passa de US$ {ex.TETO_RODADAS_USD:.2f}. Parando.")
    print(f"Projeção (estimativa) da rodada completa: US$ {proj:.4f}")
    for exp, variante in ex.ORDEM:
        if args.so and exp != args.so:
            continue
        feitas, novas, parou = ex.executar_variante(cli, exp, variante)
        print(f"== {exp} {variante}: {feitas} já existiam, {novas} novas")
        if parou:
            sys.exit(f"Parou em {exp} {variante}: {parou}\nVeja logs/erros.log. Não tente de novo em laço: relate e decida.")
    print(f"Fim. Gasto novo: US$ {ctl.gasto:.6f} de US$ {ex.TETO_RODADAS_USD:.2f}.")


if __name__ == "__main__":
    main()
