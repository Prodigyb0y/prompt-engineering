"""Valida dados/extracao/v3 (20 casos novos do T4 v2) com a mesma releitura independente da v2 e congela por hash.

  python src/validar_dados_v3.py             # valida
  python src/validar_dados_v3.py --congelar  # valida e grava CONGELADO.sha256

Além da releitura do texto, confere que nenhum caso repete texto da v1, da v2 ou dos exemplos few-shot.
"""
import hashlib
import sys
from pathlib import Path

import gerar_dados_v3 as g3
import validar_dados_v2 as v2

DADOS = Path(__file__).resolve().parent.parent / "dados" / "extracao" / "v3"
ARQUIVOS = ["casos_teste.json", "gabarito.json"]


def validar():
    try:
        v2.main(DADOS, n=g3.N, tipos_esperados={t for t, _ in g3.TIPOS}, outras_versoes=("v1", "v2"), rotulo="v3", amostra_n=20)
    except SystemExit as e:
        return e.code or 0
    return 0


def hashes():
    return {n: hashlib.sha256((DADOS / n).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for n in ARQUIVOS}


def main():
    if validar():
        sys.exit(1)
    if "--congelar" in sys.argv:
        (DADOS / "CONGELADO.sha256").write_text("".join(f"{h}  {n}\n" for n, h in hashes().items()), encoding="utf-8", newline="\n")
        print("Congelado:", ", ".join(f"{n} {h[:12]}" for n, h in hashes().items()))


if __name__ == "__main__":
    main()
