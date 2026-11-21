"""Valida dados/v2: cada texto corresponde ao gabarito, relendo o texto com regex
independentes do gerador. Sorteia 10 casos (seed 42) para revisão manual.

Uso: python src/validar_dados_v2.py   (sai com código 1 se algo falhar)
"""
import json
import random
import re
import sys
from pathlib import Path

from validar_dados import ABREV, CAMPOS, MESES, SIMB, UNIDADES

DADOS = Path(__file__).resolve().parent.parent / "dados" / "extracao" / "v2"
EXTENSO = {"três": 3, "cinco": 5, "oito": 8, "dez": 10, "doze": 12, "quinze": 15, "vinte": 20,
           "vinte e cinco": 25, "trinta": 30, "quarenta": 40, "cinquenta": 50}
PALAVRA = {"reais": "BRL", "dólares": "USD", "euros": "EUR"}


def ler_datas(texto):
    """Todas as datas com ano, em ordem de aparição, como ISO."""
    achados = []
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", texto):
        achados.append((m.start(), f"{m[1]}-{m[2]}-{m[3]}"))
    for m in re.finditer(r"\b(\d{2})/(\d{2})/(\d{4})\b", texto):
        achados.append((m.start(), f"{m[3]}-{m[2]}-{m[1]}"))
    for m in re.finditer(r"\b(\d{1,2}) de (\w+) de (\d{4})\b", texto):
        achados.append((m.start(), f"{m[3]}-{MESES[m[2]]:02d}-{int(m[1]):02d}"))
    for m in re.finditer(r"\b(\d{2})-(\w{3})-(\d{4})\b", texto):
        achados.append((m.start(), f"{m[3]}-{ABREV[m[2]]:02d}-{m[1]}"))
    return [d for _, d in sorted(achados)]


def num(n):
    if "," in n:                                   # 1.200,50 | 12,50
        n = n.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", n):   # 1.200 | 15.800 (milhar brasileiro)
        n = n.replace(".", "")
    else:                                          # 89.90 (decimal) | 1,200.00 já sem vírgula
        n = n.replace(",", "")
    return float(n)


def ler_valor_simbolo(texto):
    m = re.search(r"(R\$|US\$|€)\s*([\d.,]+\d)", texto)
    return (num(m[2]), SIMB[m[1]]) if m else (None, None)


TIPOS_V2 = {"completa", "campos_faltando", "unidades_variadas", "valor_br", "moeda_simbolo", "data_formato",
            "data_relativa", "fornecedor_apelido", "ruido", "duas_quantidades", "correcao", "valor_total",
            "numero_extenso", "moeda_extenso", "email_longo"}


def main(dados=DADOS, n=50, tipos_esperados=TIPOS_V2, outras_versoes=("v1",), rotulo="v2", amostra_n=10):
    """Valida `dados` (n casos). `outras_versoes`: pastas irmãs cujos textos o conjunto não pode repetir."""
    DADOS_ = Path(dados)
    casos = json.loads((DADOS_ / "casos_teste.json").read_text(encoding="utf-8"))
    gab = json.loads((DADOS_ / "gabarito.json").read_text(encoding="utf-8"))
    fonte = json.loads((DADOS_ / "registros_fonte.json").read_text(encoding="utf-8"))
    fewshot = json.loads((DADOS_.parent / "v1" / "exemplos_fewshot.json").read_text(encoding="utf-8"))
    v1 = [c for v in outras_versoes for c in json.loads((DADOS_.parent / v / "casos_teste.json").read_text(encoding="utf-8"))]
    erros = []

    def err(cid, msg):
        erros.append(f"{cid}: {msg}")

    if len(casos) != n or len({c["id"] for c in casos}) != n:
        erros.append(f"esperados {n} casos com ids únicos")
    for c in casos:
        cid, tipo, texto = c["id"], c["tipo"], c["texto"]
        g, ex = gab[cid], fonte[cid]["extras"]
        if set(g) != set(CAMPOS):
            err(cid, "campos do gabarito diferentes do schema")
        if g != fonte[cid]["registro"]:
            err(cid, "gabarito diverge do registro estruturado")
        if g["unidade"] not in UNIDADES or g["moeda"] not in {"BRL", "USD", "EUR", None}:
            err(cid, "enum inválido")
        if "Ltda." in texto:
            err(cid, "artefato do ponto depois de Ltda")
        if g["item"] not in texto:
            err(cid, "item ausente")
        if g["solicitante_area"] and g["solicitante_area"] not in texto:
            err(cid, "área ausente")
        if g["fornecedor"] and g["fornecedor"] not in texto:
            err(cid, "fornecedor ausente")
        if not g["fornecedor"] and re.search(r"[Ff]ornecedor:|cotação feita|Pode ser com", texto):
            err(cid, "texto cita fornecedor mas gabarito é null")
        # quantidade
        q = g["quantidade"]
        if tipo == "numero_extenso":
            achou = [v for k, v in EXTENSO.items() if re.search(rf"\b{k}\b", texto)]
            if q not in achou:
                err(cid, f"quantidade por extenso não confere ({achou} vs {q})")
        elif tipo == "correcao" and ex.get("subtipo") == "quantidade":
            if f"são {q} " not in texto or f"não {ex['q0']}" not in texto:
                err(cid, "correção de quantidade não confere")
        elif not re.search(rf"\b{q}\s?\w", texto):
            err(cid, "quantidade ausente")
        # data: vale a última data do texto
        datas = ler_datas(texto)
        esperado = datas[-1] if datas else None
        if g["prazo_entrega"] != esperado:
            err(cid, f"data lida ({esperado}) != gabarito ({g['prazo_entrega']})")
        if tipo == "data_relativa" and (g["prazo_entrega"] is not None or datas):
            err(cid, "data relativa deveria resultar em null")
        if tipo == "correcao" and ex.get("subtipo") == "prazo" and (len(datas) != 2 or datas[0] != ex["d0"]):
            err(cid, "correção de prazo não confere")
        # fornecedor corrigido
        if tipo == "correcao" and ex.get("subtipo") == "fornecedor":
            if f"fechar com {g['fornecedor']}, não com {ex['f_errado']}" not in texto or g["fornecedor"] == ex["f_errado"]:
                err(cid, "correção de fornecedor não confere")
        # valor e moeda
        if tipo == "valor_total":
            m = re.search(r"valor total (R\$|US\$|€)\s*([\d.,]+\d)", texto)
            lido = (round(num(m[2]) / q, 2), SIMB[m[1]]) if m else (None, None)
        elif tipo == "moeda_extenso":
            m = re.search(r"([\d.,]*\d)\s+(reais|dólares|euros)", texto)
            lido = (num(m[1]), PALAVRA[m[2]]) if m else (None, None)
        else:
            lido = ler_valor_simbolo(texto)
        if lido != (g["valor_unitario"], g["moeda"]):
            err(cid, f"valor/moeda lidos {lido} != gabarito ({g['valor_unitario']},{g['moeda']})")
        if (g["valor_unitario"] is None) != (g["moeda"] is None):
            err(cid, "valor e moeda devem ser ambos null ou ambos preenchidos")
        if tipo == "duas_quantidades" and str(ex["distrator"]) not in texto:
            err(cid, "distrator ausente")
        if tipo == "email_longo" and not all(s in texto for s in ["Att,", "ramal", "confidencial"]):
            err(cid, "e-mail sem saudação/assinatura/aviso")
    if {c["tipo"] for c in casos} != set(tipos_esperados):
        erros.append("cobertura de tipos diferente da esperada")
    textos = {c["texto"] for c in casos}
    if len(textos) != n:
        erros.append("textos duplicados")
    if textos & {e["entrada"] for e in fewshot}:
        erros.append("caso repete exemplo few-shot")
    if textos & {c["texto"] for c in v1}:
        erros.append("caso idêntico a um caso de outra versão dos dados")
    amostra = random.Random(42).sample([c["id"] for c in casos], min(amostra_n, n))
    print("Casos sorteados para revisão manual (seed 42):", ", ".join(sorted(amostra)))
    if erros:
        print(f"FALHOU: {len(erros)} problema(s)")
        print("\n".join(erros))
        sys.exit(1)
    print(f"OK: {n} casos {rotulo}, gabarito consistente com o registro e com a releitura independente do texto.")


if __name__ == "__main__":
    main()
