"""Classifica cada resposta errada e recalcula o acerto sob uma tolerância PÓS-HOC.

Gera resultados/ERROS.md. O resultado OFICIAL continua sendo o de resultados/RELATORIO.md
(regra de acerto definida antes de medir). A tolerância abaixo foi criada DEPOIS de ver os
resultados e é apresentada separada, marcada como pós-hoc.

Classes de erro (primeira que se aplica):
- json_invalido / schema_invalido: falha de formato.
- fornecedor_ponto_final: o único campo errado é o fornecedor e a diferença é só um ponto final
  ("Ltda." x "Ltda"). Origem: o gerador de casos usa ". " como separador de frases, então o
  texto traz "Ltda." e o modelo copia a abreviação com ponto. Artefato do caso, não do modelo.
- campo_diferente: algum campo com valor diferente do gabarito (qualquer outra causa).

Uso: python src/classificar_erros.py [pasta_brutos]
"""
import collections
import json
import sys
from pathlib import Path

import validador as v
from analisar import NOMES, bootstrap_ic, carregar

RAIZ = Path(__file__).resolve().parent.parent


def so_ponto_final(previsto, esperado) -> bool:
    return (isinstance(previsto, str) and isinstance(esperado, str) and previsto != esperado
            and previsto.strip().rstrip(".").strip().lower() == esperado.strip().rstrip(".").strip().lower()
            and v.norm_texto(previsto) != v.norm_texto(esperado))


def classificar(reg, gabarito):
    """-> (classe, caso_correto_posthoc)"""
    a = reg["avaliacao"]
    if a["caso_correto"]:
        return "correto", True
    if not a["json_valido"]:
        return "json_invalido", False
    if not a["schema_valido"]:
        return "schema_invalido", False
    obj, _ = v.parse(reg["resposta"], reg["tecnica"])
    errados = [c for c, ok in a["campos"].items() if not ok]
    if errados == ["fornecedor"] and so_ponto_final(obj.get("fornecedor"), gabarito["fornecedor"]):
        return "fornecedor_ponto_final", True
    return "campo_diferente", False


def main():
    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "resultados" / "brutos"
    gab = json.loads((RAIZ / "dados" / "gabarito.json").read_text(encoding="utf-8"))
    casos = {c["id"]: c for c in json.loads((RAIZ / "dados" / "casos_teste.json").read_text(encoding="utf-8"))}
    regs = carregar(pasta)
    cont = collections.defaultdict(collections.Counter)
    por_caso = collections.defaultdict(lambda: collections.defaultdict(list))   # tec -> caso -> [posthoc ok]
    detalhe = collections.defaultdict(collections.Counter)                      # caso -> (tec, classe)
    for r in regs:
        classe, ok_pos = classificar(r, gab[r["caso"]])
        cont[r["tecnica"]][classe] += 1
        por_caso[r["tecnica"]][r["caso"]].append(1.0 if ok_pos else 0.0)
        if classe != "correto":
            detalhe[r["caso"]][(r["tecnica"], classe)] += 1
    classes = ["json_invalido", "schema_invalido", "fornecedor_ponto_final", "campo_diferente"]
    tecs = sorted(cont)
    L = ["# Classificação dos erros", "",
         "Gerado por `python src/classificar_erros.py`. Resultado oficial: `RELATORIO.md`. Este arquivo explica os erros dele e traz uma recontagem pós-hoc.", "",
         "## Erros por classe (número de respostas erradas)", "",
         "| Classe | " + " | ".join(f"{t} {NOMES.get(t, t)}" for t in tecs) + " |", "|---|" + "---|" * len(tecs)]
    for c in classes:
        L.append(f"| {c} | " + " | ".join(str(cont[t][c]) for t in tecs) + " |")
    L.append("| total de respostas | " + " | ".join(str(sum(cont[t].values())) for t in tecs) + " |")
    L += ["", "## Casos com erro", "", "| Caso | Tipo | Erros (técnica: classe, nº de respostas) | Texto |", "|---|---|---|---|"]
    for cid in sorted(detalhe):
        e = "; ".join(f"{t}: {c} ×{n}" for (t, c), n in sorted(detalhe[cid].items()))
        L.append(f"| {cid} | {casos[cid]['tipo']} | {e} | {casos[cid]['texto'].replace(chr(10), ' ')[:110]} |")
    L += ["", "## Recontagem PÓS-HOC (não oficial)", "",
          "Tolerância: diferença de ponto final no fornecedor (\"Ltda.\" = \"Ltda\"). Criada depois de ver os resultados, "
          "por isso não substitui o resultado oficial. Mesmo método de intervalo (bootstrap, 10.000 reamostragens, seed 42).", "",
          "| Técnica | Acerto oficial | Acerto pós-hoc | IC 95% pós-hoc |", "|---|---|---|---|"]
    for t in tecs:
        ofic = sum(1 for r in regs if r["tecnica"] == t and r["avaliacao"]["caso_correto"]) / sum(1 for r in regs if r["tecnica"] == t)
        medias = [sum(x) / len(x) for x in por_caso[t].values()]
        lo, hi = bootstrap_ic(medias)
        L.append(f"| {t} {NOMES.get(t, t)} | {100 * ofic:.1f}% | {100 * sum(medias) / len(medias):.1f}% | {100 * lo:.1f}%–{100 * hi:.1f}% |")
    (RAIZ / "resultados" / "ERROS.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
