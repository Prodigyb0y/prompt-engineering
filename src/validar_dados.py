"""Valida que cada texto corresponde ao gabarito, relendo o texto com regex
independentes do gerador. Sorteia 10 casos (seed 42) para revisão manual.

Uso: python src/validar_dados.py   (sai com código 1 se algo falhar)
"""
import json
import random
import re
import sys
from pathlib import Path

DADOS = Path(__file__).resolve().parent.parent / "dados"
MESES = {m: i + 1 for i, m in enumerate(["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
                                        "agosto", "setembro", "outubro", "novembro", "dezembro"])}
ABREV = {m: i + 1 for i, m in enumerate(["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"])}
UNIDADES = {"un", "kg", "m", "l", "cx"}
CAMPOS = ["solicitante_area", "item", "quantidade", "unidade", "prazo_entrega", "valor_unitario", "moeda", "fornecedor"]
SIMB = {"R$": "BRL", "US$": "USD", "€": "EUR"}


def ler_data(texto):
    """Primeira data com ano encontrada no texto -> ISO, ou None."""
    if m := re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", texto):
        return f"{m[1]}-{m[2]}-{m[3]}"
    if m := re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", texto):
        return f"{m[3]}-{m[2]}-{m[1]}"
    if m := re.search(r"\b(\d{1,2}) de (\w+) de (\d{4})\b", texto):
        return f"{m[3]}-{MESES[m[2]]:02d}-{int(m[1]):02d}"
    if m := re.search(r"\b(\d{2})-(\w{3})-(\d{4})\b", texto):
        return f"{m[3]}-{ABREV[m[2]]:02d}-{m[1]}"
    return None


def ler_valor(texto):
    m = re.search(r"(R\$|US\$|€)\s*([\d.,]+\d)", texto)
    if not m:
        return None, None
    n = m[2]
    if "," in n:  # estilo brasileiro: 1.200,00 ou 12,50
        n = n.replace(".", "").replace(",", ".")
    else:         # estilo US: 1,200.00 já sem vírgula aqui -> 89.90
        n = n.replace(",", "")
    return float(n), SIMB[m[1]]


def main():
    casos = json.loads((DADOS / "casos_teste.json").read_text(encoding="utf-8"))
    gab = json.loads((DADOS / "gabarito.json").read_text(encoding="utf-8"))
    fonte = json.loads((DADOS / "registros_fonte.json").read_text(encoding="utf-8"))
    fewshot = json.loads((DADOS / "exemplos_fewshot.json").read_text(encoding="utf-8"))
    erros = []

    def err(cid, msg):
        erros.append(f"{cid}: {msg}")

    if len(casos) != 50 or len({c["id"] for c in casos}) != 50:
        erros.append("esperados 50 casos com ids únicos")
    for c in casos:
        cid, texto = c["id"], c["texto"]
        g = gab[cid]
        if set(g) != set(CAMPOS):
            err(cid, "campos do gabarito diferentes do schema")
        if g != fonte[cid]["registro"]:
            err(cid, "gabarito diverge do registro estruturado")
        if g["unidade"] not in UNIDADES:
            err(cid, "unidade fora do enum")
        if g["moeda"] not in {"BRL", "USD", "EUR", None}:
            err(cid, "moeda fora do enum")
        if g["item"] not in texto:
            err(cid, "item ausente do texto")
        if g["fornecedor"] and g["fornecedor"] not in texto:
            err(cid, "fornecedor ausente do texto")
        if g["solicitante_area"] and g["solicitante_area"] not in texto:
            err(cid, "área ausente do texto")
        if not g["fornecedor"] and re.search(r"[Ff]ornecedor:|cotação feita|Pode ser com", texto):
            err(cid, "texto cita fornecedor mas gabarito é null")
        if not re.search(rf"\b{g['quantidade']}\s?\w", texto):
            err(cid, "quantidade ausente do texto")
        # data: releitura independente
        d = ler_data(texto)
        if g["prazo_entrega"] != d:
            err(cid, f"data lida do texto ({d}) != gabarito ({g['prazo_entrega']})")
        if c["tipo"] == "data_relativa" and (g["prazo_entrega"] is not None or d is not None):
            err(cid, "data relativa deveria resultar em null")
        # valor/moeda
        v, m = ler_valor(texto)
        if v != g["valor_unitario"] or m != g["moeda"]:
            err(cid, f"valor/moeda lidos ({v},{m}) != gabarito ({g['valor_unitario']},{g['moeda']})")
        if (g["valor_unitario"] is None) != (g["moeda"] is None):
            err(cid, "valor e moeda devem ser ambos null ou ambos preenchidos")
        if c["tipo"] == "duas_quantidades" and str(fonte[cid]["extras"]["distrator"]) not in texto:
            err(cid, "distrator ausente")
    tipos = {c["tipo"] for c in casos}
    for t in ["completa", "campos_faltando", "unidades_variadas", "valor_br", "moeda_simbolo", "data_formato",
              "data_relativa", "fornecedor_apelido", "ruido", "duas_quantidades"]:
        if t not in tipos:
            erros.append(f"tipo sem cobertura: {t}")
    textos = {c["texto"] for c in casos}
    if len(textos) != 50:
        erros.append("textos duplicados entre casos")
    for i, ex in enumerate(fewshot):
        if ex["entrada"] in textos:
            erros.append(f"few-shot {i} é igual a um caso de teste")
    if len(fewshot) != 3:
        erros.append("esperados 3 exemplos few-shot")

    amostra = random.Random(42).sample([c["id"] for c in casos], 10)
    print("Casos sorteados para revisão manual (seed 42):", ", ".join(sorted(amostra)))
    if erros:
        print(f"FALHOU: {len(erros)} problema(s)")
        print("\n".join(erros))
        sys.exit(1)
    print("OK: 50 casos, gabarito consistente com registro e com a releitura independente do texto.")


if __name__ == "__main__":
    main()
