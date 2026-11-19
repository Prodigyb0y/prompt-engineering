"""Gera a v2 dos dados fictícios (seed 42) em dados/v2/.

Mudanças em relação à v1:
- Corrige o artefato da v1: o gerador nunca coloca ponto depois de "Ltda" (nem como separador
  de frases nem no fim do texto). Gabarito e texto concordam sobre o nome do fornecedor.
- Mantém os 10 tipos da v1 (27 casos) e acrescenta 5 tipos mais difíceis (23 casos):
  correcao, valor_total, numero_extenso, moeda_extenso, email_longo.
- Os 3 exemplos few-shot NÃO mudam (continuam em dados/exemplos_fewshot.json), para os prompts
  v1 ficarem idênticos (mesmos hashes). Só o conjunto de casos muda.

Regras de rotulagem novas (valem para o gabarito v2):
- correcao: vale o último valor dito (quantidade, fornecedor ou prazo corrigidos no próprio texto).
- valor_total: valor_unitario = valor total / quantidade.
- numero_extenso: a quantidade escrita por extenso vira número.
- moeda_extenso: "reais" = BRL, "dólares" = USD, "euros" = EUR.
- email_longo: mensagem com saudação, contexto, assinatura, ramal e aviso; só o pedido conta.

Uso: python src/gerar_dados_v2.py
"""
import json
import random
from pathlib import Path

import gerar_dados as g1

SEED = 42
SAIDA = g1.DADOS / "v2"
CAMPOS = ["solicitante_area", "item", "quantidade", "unidade", "prazo_entrega", "valor_unitario", "moeda", "fornecedor"]

TIPOS = [("completa", 3), ("campos_faltando", 3), ("unidades_variadas", 3), ("valor_br", 3), ("moeda_simbolo", 2),
         ("data_formato", 3), ("data_relativa", 3), ("fornecedor_apelido", 2), ("ruido", 3), ("duas_quantidades", 2),
         ("correcao", 5), ("valor_total", 4), ("numero_extenso", 4), ("moeda_extenso", 4), ("email_longo", 6)]
EXTENSO = {3: "três", 5: "cinco", 8: "oito", 10: "dez", 12: "doze", 15: "quinze", 20: "vinte",
           25: "vinte e cinco", 30: "trinta", 40: "quarenta", 50: "cinquenta"}
PALAVRA_MOEDA = {"BRL": "reais", "USD": "dólares", "EUR": "euros"}
PRECOS_TOTAL = [4.5, 8.9, 12.5, 35, 49.9, 120, 380]
QTD_TOTAL = [4, 5, 8, 10, 20, 25, 40]


def num_br(v):
    """Número no estilo brasileiro sem símbolo: 1.200 | 89,90 | 310."""
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s[:-3] if s.endswith(",00") else s


def pecas(rec, rng, qtd_txt=None, valor_txt=None, prazo_txt=None, forn_txt=None, estilo_valor="simples"):
    """Frases do pedido (sem pontuação final) e os trechos usados."""
    t = {}
    un = rng.choice(g1.UNID_TXT[rec["unidade"]])
    qtd = qtd_txt or f"{rec['quantidade']} {un}"
    t["qtd_txt"] = qtd
    ab = rng.choice([f"Oi, preciso de {qtd} de {rec['item']}", f"Bom dia! Solicito {qtd} de {rec['item']}",
                     f"Pedido de compra: {qtd} de {rec['item']}", f"Preciso comprar {qtd} de {rec['item']}"])
    if rec["solicitante_area"]:
        ab += rng.choice([f" para a área de {rec['solicitante_area']}", f" (solicitante: {rec['solicitante_area']})"])
    out = [ab]
    if rec["valor_unitario"] is not None:
        v = valor_txt or g1.fmt_valor(rec["valor_unitario"], rec["moeda"], estilo_valor)
        t["valor_txt"] = v
        out.append(rng.choice([f"Valor unitário {v}", f"Cada unidade custa {v}", f"preço de tabela: {v} por unidade"])
                   if not valor_txt or "total" not in valor_txt else v)
    if rec["fornecedor"]:
        nome = forn_txt or rec["fornecedor"]
        t["forn_txt"] = nome
        out.append(rng.choice([f"Fornecedor: {nome}", f"Pode ser com a {nome}", f"cotação feita com {nome}"]))
    if rec["prazo_entrega"] or prazo_txt:
        d = prazo_txt or g1.fmt_data(rec["prazo_entrega"], rec.get("_estilo") or rng.choice(["barra", "extenso", "iso", "abrev"]))
        t["prazo_txt"] = d
        out.append(rng.choice([f"Entrega até {d}", f"Prazo: {d}", f"precisa chegar em {d}"]))
    return out, t


def juntar(partes, rng, final=True):
    """Junta frases sem nunca deixar ponto depois de 'Ltda'."""
    txt = partes[0]
    for p in partes[1:]:
        sep = rng.choice([". ", "\n", "; ", " – "])
        if sep == ". " and txt.endswith("Ltda"):
            sep = "; "
        txt += sep + p
    if final and not txt.endswith("Ltda") and rng.random() < 0.8:
        txt += "."
    return txt


def montar(rng, tipo, usados):
    rec = g1.registro_base(rng, usados)
    meta = {}
    partes_extra_depois = []
    qtd_txt = valor_txt = prazo_txt = forn_txt = None
    estilo_valor = "simples"

    if tipo == "campos_faltando":
        for campo in rng.sample(["solicitante_area", "prazo_entrega", "valor_unitario", "fornecedor"], rng.choice([1, 2, 3])):
            rec[campo] = None
        if rec["valor_unitario"] is None:
            rec["moeda"] = None
    elif tipo == "unidades_variadas":
        rec["unidade"] = rng.choice(["cx", "kg", "m", "l", "un"])
        rec["item"] = rng.choice([i for i, u in g1.ITENS.items() if rec["unidade"] in u] or [rec["item"]])
        un = rng.choice(g1.UNID_TXT[rec["unidade"]])
        qtd_txt = f"{rec['quantidade']}{rng.choice(['', ' '])}{un}"
    elif tipo == "valor_br":
        rec["valor_unitario"] = round(rng.choice([1200, 2450.75, 15800, 3499.9, 1050.5, 12999]), 2)
        estilo_valor = "br"
    elif tipo == "moeda_simbolo":
        rec["moeda"] = rng.choice(["USD", "EUR"])
        rec["valor_unitario"] = round(rng.choice([3.9, 14.5, 27, 89.9, 310]), 2)
        estilo_valor = "us" if rec["moeda"] == "USD" and rng.random() < 0.5 else "simples"
    elif tipo == "data_formato":
        rec["_estilo"] = rng.choice(["barra", "extenso", "iso", "abrev"])
    elif tipo == "data_relativa":
        rec["prazo_entrega"] = None
        meta["prazo_relativo"] = rng.choice(["daqui 15 dias", "na semana que vem", "em 10 dias úteis", "o quanto antes, daqui uns 20 dias"])
        partes_extra_depois.append(f"Entrega {meta['prazo_relativo']}")
    elif tipo == "fornecedor_apelido":
        rec["fornecedor"] = g1.FORNECEDORES[rec["fornecedor"]]
    elif tipo == "duas_quantidades":
        meta["distrator"] = rng.choice([x for x in [2, 3, 7, 9, 30, 60] if x != rec["quantidade"]])
    elif tipo == "correcao":
        sub = rng.choice(["quantidade", "fornecedor", "prazo"])
        meta["subtipo"] = sub
        if sub == "quantidade":
            q0 = rng.choice([x for x in [2, 3, 4, 5, 8, 10, 12, 15, 20, 25, 40, 50] if x != rec["quantidade"]])
            un = rng.choice(g1.UNID_TXT[rec["unidade"]])
            qtd_txt = f"{q0} {un}"
            meta["q0"] = q0
            partes_extra_depois.append(f"Corrigindo: são {rec['quantidade']} {un}, não {q0}")
        elif sub == "fornecedor":
            if rec["fornecedor"] is None:
                rec["fornecedor"] = rng.choice(list(g1.FORNECEDORES))
            errado = rng.choice([f for f in g1.FORNECEDORES if f != rec["fornecedor"]])
            forn_txt = errado
            meta["f_errado"] = errado
            partes_extra_depois.append(f"Mudou: vamos fechar com {rec['fornecedor']}, não com {errado}")
        else:
            d0 = g1.data_aleatoria(rng)
            while d0 == rec["prazo_entrega"]:
                d0 = g1.data_aleatoria(rng)
            est = rng.choice(["barra", "extenso", "iso", "abrev"])
            prazo_txt = g1.fmt_data(d0, est)
            meta["d0"] = d0
            partes_extra_depois.append(f"Melhor ficar para {g1.fmt_data(rec['prazo_entrega'], est)}")
    elif tipo == "valor_total":
        preco = rng.choice(PRECOS_TOTAL)
        q = rng.choice(QTD_TOTAL)
        total = round(preco * q, 2)
        assert round(total / q, 2) == preco
        rec["quantidade"], rec["valor_unitario"] = q, preco
        rec["moeda"] = rng.choice(["BRL", "BRL", "USD", "EUR"])
        valor_txt = "valor total " + g1.fmt_valor(total, rec["moeda"], rng.choice(["br", "simples"]))
        meta["total"] = total
    elif tipo == "numero_extenso":
        rec["quantidade"] = rng.choice(list(EXTENSO))
        qtd_txt = f"{EXTENSO[rec['quantidade']]} {rng.choice(g1.UNID_TXT[rec['unidade']][1:])}"
    elif tipo == "moeda_extenso":
        rec["moeda"] = rng.choice(["BRL", "USD", "EUR"])
        rec["valor_unitario"] = round(rng.choice([35, 89.9, 120, 310, 1200, 2450.75]), 2)
        valor_txt = f"{num_br(rec['valor_unitario'])} {PALAVRA_MOEDA[rec['moeda']]}"
        meta["valor_extenso"] = valor_txt
    elif tipo == "email_longo":
        rec["solicitante_area"] = rec["solicitante_area"] or rng.choice(g1.AREAS)

    partes, trechos = pecas(rec, rng, qtd_txt, valor_txt, prazo_txt, forn_txt, estilo_valor)
    if tipo == "duas_quantidades":
        partes.insert(1, rng.choice([f"Hoje temos {meta['distrator']} em estoque, mas não dá",
                                     f"O último pedido foi de {meta['distrator']}, agora é diferente"]))
    partes += partes_extra_depois

    if tipo == "email_longo":
        contexto = rng.choice(["Conforme conversamos ontem na reunião, segue o pedido.",
                               "Espero que esteja tudo bem. Seguem os dados da nossa necessidade.",
                               "Sobre aquele assunto do almoxarifado, já alinhei com o gestor."])
        corpo = juntar(partes, rng)
        texto = (f"Olá, time de Compras,\n\n{contexto}\n\n{corpo}\n\nQualquer dúvida, é só chamar.\nAtt,\n"
                 f"Equipe de {rec['solicitante_area']}\nramal {rng.randint(3000, 4999)}\n\n"
                 "Esta mensagem é confidencial e destinada apenas ao destinatário.")
    elif tipo == "ruido":
        txt = juntar(partes, rng, final=False)
        for a, b in list({"preciso": "presiso", "Entrega": "Entrga", "Fornecedor": "Fornecedro", "valor": "valro"}.items())[: rng.choice([2, 3, 4])]:
            txt = txt.replace(a, b)
        sufixo = rng.choice([" obrigado!!", " abs", "\n\n-- enviado do meu celular"])
        texto = rng.choice(["att, ", "obs: ", "URGENTE!! ", "kkk, "]) + txt + ("" if txt.endswith("Ltda") else sufixo)
    else:
        texto = juntar(partes, rng)

    assert "Ltda." not in texto, "artefato do ponto depois de Ltda"
    gab = {k: rec[k] for k in CAMPOS}
    return gab, texto, {**trechos}, meta


def main():
    rng = random.Random(SEED)
    usados = set()
    casos, gabarito, fonte = [], {}, {}
    n = 0
    for tipo, qtd in TIPOS:
        for _ in range(qtd):
            n += 1
            cid = f"D{n:02d}"
            gab, texto, trechos, meta = montar(rng, tipo, usados)
            casos.append({"id": cid, "tipo": tipo, "texto": texto})
            gabarito[cid] = gab
            fonte[cid] = {"tipo": tipo, "registro": gab, "trechos": trechos, "extras": meta}
    assert len(casos) == 50 and sum(q for _, q in TIPOS) == 50
    rng.shuffle(casos)
    fewshot = json.loads((g1.DADOS / "exemplos_fewshot.json").read_text(encoding="utf-8"))
    assert not ({c["texto"] for c in casos} & {e["entrada"] for e in fewshot}), "caso v2 repete exemplo few-shot"
    SAIDA.mkdir(parents=True, exist_ok=True)
    for nome, obj in [("casos_teste.json", casos), ("gabarito.json", gabarito), ("registros_fonte.json", fonte)]:
        (SAIDA / nome).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"v2 gerada: {len(casos)} casos em {SAIDA} (seed {SEED}); few-shot e prompts continuam os da v1.")


if __name__ == "__main__":
    main()
