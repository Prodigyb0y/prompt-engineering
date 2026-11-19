"""Gera dados fictícios (empresa fictícia Gutenberg Systems) com semente fixa.

Fluxo: registro estruturado -> gabarito (direto do registro) e texto (renderizado
a partir do registro). O gabarito nunca é copiado de um modelo.

Saídas em dados/:
  registros_fonte.json     registro estruturado + trechos renderizados (usado na validação)
  casos_teste.json         50 casos: id, tipo, texto
  gabarito.json            id -> JSON correto
  exemplos_fewshot.json    3 exemplos (texto + saída), disjuntos dos casos de teste

Uso: python src/gerar_dados.py
"""
import json
import random
from pathlib import Path

SEED = 42
DADOS = Path(__file__).resolve().parent.parent / "dados"

AREAS = ["Compras", "Manutenção", "TI", "Logística", "Financeiro", "Produção", "RH", "Marketing"]
ITENS = {  # item: unidades plausíveis
    "papel A4": ["cx", "un"], "toner preto": ["un"], "cabo de rede cat6": ["m", "un"],
    "parafuso sextavado": ["cx", "kg"], "tinta acrílica branca": ["l"], "álcool isopropílico": ["l"],
    "fita adesiva": ["un", "cx"], "luva de proteção": ["cx", "un"], "cabo elétrico 2,5mm": ["m"],
    "teclado sem fio": ["un"], "monitor 24 polegadas": ["un"], "solda em barra": ["kg"],
    "óleo lubrificante": ["l"], "etiqueta adesiva": ["cx"], "caneta esferográfica": ["cx", "un"],
    "tubo PVC 50mm": ["m"], "cadeira ergonômica": ["un"], "detergente industrial": ["l"],
}
FORNECEDORES = {  # nome completo (fictício): apelido
    "Papelaria Aurora Ltda": "Aurora", "Metalúrgica Vale Verde": "Vale Verde",
    "Distribuidora Pinheiro": "Pinheiro", "Químicos Horizonte": "Horizonte",
    "Tecidos Santa Clara": "Santa Clara", "Embalagens Ponto Certo": "Ponto Certo",
    "Eletrotécnica Faísca": "Faísca", "Informática Bitmais": "Bitmais",
}
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
MES_ABREV = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
UNID_TXT = {"un": ["un", "unidades"], "kg": ["kg", "quilos"], "m": ["m", "metros"],
            "l": ["l", "litros"], "cx": ["cx", "caixas"]}

# Tipos e quantidade de casos de cada um (soma = 50)
TIPOS = [("completa", 8), ("campos_faltando", 6), ("unidades_variadas", 6),
         ("valor_br", 6), ("moeda_simbolo", 5), ("data_formato", 6),
         ("data_relativa", 4), ("fornecedor_apelido", 3), ("ruido", 3),
         ("duas_quantidades", 3)]


def fmt_valor(v, moeda, estilo):
    """Renderiza o valor no texto. estilo: br (1.200,00), us (1,200.00), simples (12,50)."""
    simbolo = {"BRL": "R$", "USD": "US$", "EUR": "€"}[moeda]
    if estilo == "br":
        s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    elif estilo == "us":
        s = f"{v:,.2f}"
    else:
        s = f"{v:.2f}".replace(".", ",")
    return f"{simbolo} {s}"


def fmt_data(iso, estilo):
    a, m, d = iso.split("-")
    if estilo == "iso":
        return iso
    if estilo == "barra":
        return f"{d}/{m}/{a}"
    if estilo == "extenso":
        return f"{int(d)} de {MESES[int(m) - 1]} de {a}"
    if estilo == "abrev":
        return f"{d}-{MES_ABREV[int(m) - 1]}-{a}"
    raise ValueError(estilo)


def data_aleatoria(rng):
    return f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"


def registro_base(rng, usados):
    item = rng.choice([i for i in ITENS if i not in usados] or list(ITENS))
    usados.add(item)
    unidade = rng.choice(ITENS[item])
    return {
        "solicitante_area": rng.choice(AREAS), "item": item,
        "quantidade": rng.choice([2, 3, 4, 5, 8, 10, 12, 15, 20, 25, 40, 50, 100]),
        "unidade": unidade, "prazo_entrega": data_aleatoria(rng),
        "valor_unitario": round(rng.choice([4.5, 8.9, 12.5, 35, 49.9, 120, 380, 1200, 2450.75]), 2),
        "moeda": "BRL", "fornecedor": rng.choice(list(FORNECEDORES)),
    }


def render(rec, rng, tipo):
    """Gera (texto, trechos) a partir do registro. trechos = substrings exatas usadas."""
    t = {}  # trechos renderizados, para a validação conferir
    partes = []
    un_txt = rng.choice(UNID_TXT[rec["unidade"]])
    qtd = f"{rec['quantidade']} {un_txt}" if tipo != "unidades_variadas" else f"{rec['quantidade']}{rng.choice(['', ' '])}{un_txt}"
    t["quantidade"] = str(rec["quantidade"])
    t["unidade"] = un_txt
    t["item"] = rec["item"]

    abertura = rng.choice([
        f"Oi, preciso de {qtd} de {rec['item']}", f"Bom dia! Solicito {qtd} de {rec['item']}",
        f"Pedido de compra: {qtd} de {rec['item']}", f"Preciso comprar {qtd} de {rec['item']}",
    ])
    if rec["solicitante_area"]:
        abertura += rng.choice([f" para a área de {rec['solicitante_area']}",
                                f" (solicitante: {rec['solicitante_area']})"])
        t["solicitante_area"] = rec["solicitante_area"]
    partes.append(abertura)

    if rec["valor_unitario"] is not None:
        estilo = t_estilo = ("br" if tipo in ("valor_br", "completa") else
                             "us" if rec["moeda"] == "USD" and rng.random() < 0.5 else "simples")
        v = fmt_valor(rec["valor_unitario"], rec["moeda"], estilo)
        t["valor_unitario"] = v
        partes.append(rng.choice([f"Valor unitário {v}", f"Cada unidade custa {v}", f"preço de tabela: {v} por unidade"]))
    if rec["fornecedor"]:
        nome = rec.get("_fornecedor_texto", rec["fornecedor"])
        t["fornecedor"] = nome
        partes.append(rng.choice([f"Fornecedor: {nome}", f"Pode ser com a {nome}", f"cotação feita com {nome}"]))
    if rec["prazo_entrega"]:
        estilo = rec.get("_estilo_data") or rng.choice(["barra", "extenso", "iso", "abrev"])
        d = fmt_data(rec["prazo_entrega"], estilo)
        t["prazo_entrega"] = d
        partes.append(rng.choice([f"Entrega até {d}", f"Prazo: {d}", f"precisa chegar em {d}"]))
    elif rec.get("_prazo_relativo"):
        t["prazo_relativo"] = rec["_prazo_relativo"]
        partes.append(f"Entrega {rec['_prazo_relativo']}")
    return partes, t


def montar_caso(rng, tipo, usados):
    rec = registro_base(rng, usados)
    extras = {}  # metadados de teste (não vão para o gabarito)
    if tipo == "campos_faltando":
        for campo in rng.sample(["solicitante_area", "prazo_entrega", "valor_unitario", "fornecedor"], rng.choice([1, 2, 3])):
            rec[campo] = None
        if rec["valor_unitario"] is None:
            rec["moeda"] = None
    elif tipo == "unidades_variadas":
        rec["unidade"] = rng.choice(["cx", "kg", "m", "l", "un"])
        rec["item"] = rng.choice([i for i, u in ITENS.items() if rec["unidade"] in u] or [rec["item"]])
    elif tipo == "valor_br":
        rec["valor_unitario"] = round(rng.choice([1200, 2450.75, 15800, 3499.9, 1050.5, 12999]), 2)
    elif tipo == "moeda_simbolo":
        rec["moeda"] = rng.choice(["USD", "EUR"])
        rec["valor_unitario"] = round(rng.choice([3.9, 14.5, 27, 89.9, 310]), 2)
    elif tipo == "data_formato":
        rec["_estilo_data"] = rng.choice(["barra", "extenso", "iso", "abrev"])
    elif tipo == "data_relativa":
        rec["prazo_entrega"] = None
        rec["_prazo_relativo"] = rng.choice(["daqui 15 dias", "na semana que vem", "em 10 dias úteis", "o quanto antes, daqui uns 20 dias"])
    elif tipo == "fornecedor_apelido":
        completo = rec["fornecedor"]
        rec["fornecedor"] = FORNECEDORES[completo]  # regra: fornecedor = nome como aparece no texto
        rec["_fornecedor_texto"] = FORNECEDORES[completo]
    partes, trechos = render(rec, rng, tipo)

    if tipo == "duas_quantidades":
        # Segunda quantidade distrai (ex.: estoque atual); a correta é a do item pedido.
        distrator = rng.choice([x for x in [2, 3, 7, 9, 30, 60] if x != rec["quantidade"]])
        frase = rng.choice([f"Hoje temos {distrator} em estoque, mas não dá", f"O último pedido foi de {distrator}, agora é diferente"])
        partes.insert(1, frase)
        extras["distrator"] = distrator
    if tipo == "ruido":
        trocas = {"preciso": "presiso", "entrega": "entrga", "fornecedor": "fornecedro", "valor": "valro"}
        txt = ". ".join(partes)
        for a, b in list(trocas.items())[: rng.choice([2, 3])]:
            txt = txt.replace(a, b).replace(a.capitalize(), b.capitalize())
        txt = rng.choice(["att, ", "obs: ", "URGENTE!! ", "kkk, "]) + txt + rng.choice([" obrigado!!", " abs", " \n\n-- enviado do meu celular"])
        texto = txt
    else:
        texto = ". ".join(partes) + "."
    gab = {k: rec[k] for k in ["solicitante_area", "item", "quantidade", "unidade",
                               "prazo_entrega", "valor_unitario", "moeda", "fornecedor"]}
    return gab, texto, trechos, extras


def main():
    rng = random.Random(SEED)
    usados = set()
    casos, gabarito, fonte = [], {}, {}
    n = 0
    for tipo, qtd in TIPOS:
        for _ in range(qtd):
            n += 1
            cid = f"C{n:02d}"
            gab, texto, trechos, extras = montar_caso(rng, tipo, usados)
            casos.append({"id": cid, "tipo": tipo, "texto": texto})
            gabarito[cid] = gab
            fonte[cid] = {"tipo": tipo, "registro": gab, "trechos": trechos, "extras": extras}
    assert len(casos) == 50
    # Embaralha a ordem (seed fixa) para os tipos não virem em bloco
    rng.shuffle(casos)

    # Few-shot: gerador separado (seed+1), itens e redação próprios, fora de casos_teste.
    rng_fs = random.Random(SEED + 1)
    fewshot = []
    usados_fs = set()
    textos_teste = {c["texto"] for c in casos}
    for tipo in ["completa", "campos_faltando", "data_relativa"]:
        while True:
            gab, texto, _, _ = montar_caso(rng_fs, tipo, usados_fs)
            if texto not in textos_teste:
                break
        fewshot.append({"entrada": texto, "saida": gab})

    DADOS.mkdir(exist_ok=True)
    for nome, obj in [("casos_teste.json", casos), ("gabarito.json", gabarito),
                      ("registros_fonte.json", fonte), ("exemplos_fewshot.json", fewshot)]:
        (DADOS / nome).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Gerados: {len(casos)} casos, {len(gabarito)} gabaritos, {len(fewshot)} exemplos few-shot (seed {SEED}).")


if __name__ == "__main__":
    main()
