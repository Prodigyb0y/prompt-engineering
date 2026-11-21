"""Textos em linguagem de negócio escritos A PARTIR do diagnóstico (src/diagnostico.py).

Cada função recebe o dicionário do diagnóstico e monta frases com os números dele; nenhum número é digitado aqui.
O diagnóstico é feito depois da medição, então estes textos explicam o resultado, não o prevêem.
"""
from analisar_biblioteca import pct


def _lista(itens, junta="e"):
    itens = list(itens)
    if not itens:
        return "nenhum"
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + f" {junta} " + itens[-1]


def _par(x):
    return f"{x['esperada'] if 'esperada' in x else x['esperado']} → {x['obtida'] if 'obtida' in x else x['obtido']}"


# ------------------------------------------------------------------ P2 / E3
def explicacao_e3(d):
    z, f = d["E3"]["zero_shot"], d["E3"]["few_shot"]
    pares_z = _lista(f"{_par(t)} ({t['n']})" for t in z["urgencia_esperada_obtida"])
    campo_z = z["campo_errado"]
    so_urgencia = set(campo_z) == {"urgencia"}
    p1 = (f"O zero-shot errou {z['erradas']} de {z['respostas']} respostas, {'todas na urgência' if so_urgencia else 'em campos variados'} "
          f"({pares_z}), em {len(z['casos'])} pedidos ({_lista(z['casos'])}); a categoria {'nunca errou' if 'categoria' not in campo_z else 'também errou'}.")
    if z["erradas_em_casos_com_prazo_no_texto"] == z["erradas"]:
        p1 += " Todos esses pedidos trazem um prazo no texto (\"até sexta\", \"até o fim da semana\"): sem exemplo, o modelo tratou o prazo como pouco urgente."
    ult = f["urgencia_esperada_obtida"]
    p2 = (f"Com 6 exemplos, o few-shot errou {f['erradas']} de {f['respostas']}" + (f" ({_lista(_par(t) for t in ult)}, no pedido {_lista(f['casos'])})." if ult else ".")
          + " Os exemplos ensinam a convenção da empresa para prazo e urgência, que a definição escrita não deixa clara.")
    return {"titulo": "Por que o resultado saiu assim", "paragrafos": [p1, p2]}


def aprendi_p2(d):
    e = explicacao_e3(d)["paragrafos"]
    return " ".join(e) + " Lição: definições bastam para a categoria; a urgência é uma convenção e precisa de exemplo."


# ------------------------------------------------------------------ P3 / E4
def _e4(d):
    return d["E4"]["encadeado"], d["E4"]["unico"], d["E4"]["extracao_p1_certa_em_todas"]


def explicacao_e4(d):
    enc, uni, ext = _e4(d)
    ce, cu = enc["classes"], uni["classes"]
    p1 = (f"Onde o encadeamento falharia? No erro que passa da extração para o e-mail. Não foi o caso: a extração do P1 estava certa em {ext['certas']} de {ext['de']} respostas, "
          f"e em {enc['extracao_p1_errada_nas_erradas']} dos {enc['erradas']} erros do encadeado a extração estava errada.")
    p2 = (f"Os {enc['erradas']} erros do encadeado são de dois tipos: {ce.get('so_confirmou_dado_recebido', 0)} só confirmaram um dado recebido (\"com fornecedor X\"), o que quebra a regra "
          f"\"nunca cite\" do prompt mas não pede nada de novo, e {ce.get('pediu_campo_que_ja_tinha', 0)} pediram de novo um campo que já tinha. "
          f"Nenhum e-mail deixou de pedir um campo que faltava ({ce.get('esqueceu_campo', 0)} casos).")
    p3 = (f"No prompt único, {cu.get('pediu_campo_que_ja_tinha', 0)} dos {uni['erradas']} erros foram pedir de novo um campo que já tinha, e {uni['pediu_area_compras']} deles foram a área solicitante em pedidos "
          f"cuja área era \"Compras\", o mesmo nome da equipe que assina o e-mail. No encadeado, em que o JSON já traz a área, isso aconteceu {enc['pediu_area_compras']} vez(es).")
    p4 = (f"Reanálise feita depois de ler os erros: se só contasse como erro o campo pedido de novo (e não o apenas mencionado), o encadeado teria {pct(enc['acerto_pedido'])} e o prompt único {pct(uni['acerto_pedido'])}, "
          f"contra {pct(enc['acerto_oficial'])} e {pct(uni['acerto_oficial'])} pela regra oficial. Essa regra foi escrita depois de ver os erros e não substitui o número oficial: ela mostra que a conclusão depende de como se define erro.")
    return {"titulo": "Por que o resultado saiu assim (e onde o encadeamento falha)", "paragrafos": [p1, p2, p3, p4]}


def quando_usar_e4(d):
    enc, uni, ext = _e4(d)
    ce, cu = enc["classes"], uni["classes"]
    return (f"O encadeado e o prompt único ficaram próximos pela regra oficial ({pct(enc['acerto_oficial'])} contra {pct(uni['acerto_oficial'])}). Lendo os erros, o encadeado pediu de novo um campo que já tinha "
            f"{ce.get('pediu_campo_que_ja_tinha', 0)} vez(es), contra {cu.get('pediu_campo_que_ja_tinha', 0)} do prompt único, e nunca por erro de extração. "
            "Encadeie quando o dado intermediário (o JSON) ajudar a evitar ambiguidade ou quando você precisar auditá-lo; em qualquer dos dois, escreva o que o e-mail deve fazer com os dados já recebidos, não só o que não citar.")


def aprendi_p3(d):
    enc, uni, ext = _e4(d)
    ce = enc["classes"]
    return (f"Nas {enc['respostas']} respostas do fluxo encadeado, {enc['erradas']} saíram erradas pela regra oficial. Nenhuma deixou de pedir um campo que faltava; {ce.get('so_confirmou_dado_recebido', 0)} só confirmaram "
            f"um dado já recebido (por exemplo, \"com fornecedor X\"), quebrando a regra \"nunca cite\" sem pedir nada de novo, e {ce.get('pediu_campo_que_ja_tinha', 0)} pediram de novo um campo que já tinha. "
            f"A extração do P1 estava certa em {ext['certas']} de {ext['de']}, então o erro nasce no e-mail, não na passagem entre os dois prompts. "
            "Lição: \"nunca cite\" não bastou. Hipótese para a próxima versão: dizer o que fazer no lugar (abrir só com o item e a quantidade) e listar cada campo pedido em uma linha.")


def conclusao_e4(d, a_enc, a_uni):
    enc, uni, _ = _e4(d)
    return {"titulo": "Encadear ou não depende de como se conta o erro.",
            "texto": (f"Pela regra oficial, o encadeado acertou {pct(a_enc)} contra {pct(a_uni)} do prompt único (E4). Lendo os erros, o encadeado pediu de novo um campo que já tinha "
                      f"{enc['classes'].get('pediu_campo_que_ja_tinha', 0)} vez(es), contra {uni['classes'].get('pediu_campo_que_ja_tinha', 0)}, e nunca errou por extração do P1; a maior parte dos erros dele foi só confirmar um dado recebido. "
                      f"Contando só o que o e-mail pede de novo (regra escrita depois de ler os erros), o resultado se inverte: {pct(enc['acerto_pedido'])} contra {pct(uni['acerto_pedido'])}.")}


# ------------------------------------------------------------------ P4
def aprendi_p4(d):
    p = d["P4"]
    pares = _lista(f"{_par(t)} ({t['n']})" for t in p["sentimento_esperado_obtido"])
    so_sent = set(p["campo_errado"]) == {"sentimento"}
    t = (f"{p['erradas']} de {p['respostas']} respostas erradas, {'todas no sentimento' if so_sent else 'em campos variados'} ({pares}). "
         "O modelo foi para o rótulo do meio (\"insatisfeito\") quando o cliente apenas pede uma informação, sem emoção explícita, e quando a emoção é forte. "
         "A regra de sentimento do prompt separa os três por palavras, e o reclamante que só cobra uma previsão ficou numa zona cinzenta que o meu gabarito resolveu de um jeito e o modelo de outro.")
    if p["invencoes"] == 0:
        t += " O \"não inventar\" funcionou: nenhum número de pedido ou valor foi inventado."
    return t


# ------------------------------------------------------------------ P5 / E5
def explicacao_e5(d):
    dir_, cot = d["E5"]["direto"], d["E5"]["cot"]
    casos = sorted({t["caso"] for t in dir_["erros"]})
    sub = sorted({t["subtipo"] for t in dir_["erros"]})
    p1 = (f"Com raciocínio, a decisão saiu certa em {cot['respostas'] - cot['erradas']} de {cot['respostas']} respostas. Sem raciocínio, os {dir_['erradas']} erros foram todos no mesmo pedido "
          f"({_lista(casos)}, tipo \"{_lista(sub)}\"), que reúne dois motivos para escalar ao mesmo tempo (fornecedor fora da lista e item controlado).")
    p2 = ""
    if dir_.get("com_duas_decisoes"):
        p2 = (f" Em {dir_['com_duas_decisoes']} {'resposta' if dir_['com_duas_decisoes'] == 1 else 'respostas'} o modelo escreveu uma decisão errada, se corrigiu no meio do texto e entregou duas decisões na mesma saída: "
              "a final estava certa, mas um código não consegue ler duas respostas, e por isso conta como erro.")
    p3 = "Quando duas regras da política disparam juntas, deixar o modelo escrever o raciocínio antes foi o que evitou o erro."
    return {"titulo": "Por que o resultado saiu assim", "paragrafos": [p1 + p2, p3]}


def aprendi_p5(d):
    return " ".join(explicacao_e5(d)["paragrafos"])
