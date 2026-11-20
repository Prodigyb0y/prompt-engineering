"""Gera os dados fictícios de P2 a P5 (empresa fictícia Gutenberg Systems), 20 casos cada, seed fixa.

O gabarito é ESCRITO junto com o caso (rótulo explícito em cada modelo de texto, ou regra em código no
P5) e nunca vem de um modelo de linguagem. Depois de validado e revisado, congela-se com SHA-256.

Saídas em dados/biblioteca/<p2|p3|p4|p5>/:
  casos_teste.json      id, tipo (claro ou borda), texto
  gabarito.json         id -> resposta esperada
  registros_fonte.json  de onde cada caso saiu (para a validação)

Uso: python src/gerar_dados_biblioteca.py
"""
import json
import random
from decimal import Decimal
from pathlib import Path

import gerar_dados as g1
import prompts_biblioteca as pb

SEED = 2027
RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados" / "biblioteca"
N = 20

SISTEMAS = ["sistema de estoque", "portal de compras", "sistema de contratos", "sistema de faturamento", "painel de vendas"]
SALAS = ["Aurora", "Pinheiro", "Horizonte", "Faísca"]
PROGRAMAS = ["editor de planilhas", "leitor de PDF", "software de projetos", "programa de videoconferência"]


# ------------------------------------------------------------------ P2: classificar suporte
# (id, categoria, urgencia, tipo, texto com {slots}). Escritos à mão; sorteio só preenche os {slots}.
P2_MODELOS = [
    ("claro", "acesso", "media", "Preciso de acesso ao {sistema} para o novo estagiário de {area}, que começa na segunda. Dá para liberar até o fim da semana?"),
    ("claro", "acesso", "alta", "Minha conta do {sistema} foi bloqueada depois de errar a senha e não consigo trabalhar. Não tenho outro acesso."),
    ("claro", "equipamento", "baixa", "Quando der, podem trocar o mouse da minha mesa? O scroll está meio duro, mas funciona."),
    ("claro", "equipamento", "alta", "O notebook não liga mais desde hoje cedo e não tenho máquina reserva. Sou da área de {area} e preciso entregar um relatório hoje."),
    ("claro", "software", "media", "O {sistema} trava toda vez que exporto um relatório grande. Consigo exportar em partes, mas perco tempo."),
    ("claro", "software", "baixa", "Seria possível atualizar o {programa} para a versão nova quando houver uma janela? Sem pressa."),
    ("claro", "rede", "critica", "A internet do {andar}º andar caiu inteira. Toda a equipe de {area} está parada."),
    ("claro", "rede", "media", "O wi-fi da sala de reunião {sala} está lento, mas no cabo funciona normal."),
    ("claro", "instalacoes", "baixa", "A lâmpada da minha baia queimou. Troquem quando puderem."),
    ("claro", "instalacoes", "critica", "Cheiro forte de gás na copa do {andar}º andar. As pessoas já saíram do local."),
    ("claro", "folha_beneficios", "media", "O holerite de {mes} veio com um desconto de vale-refeição que não entendi. Podem me explicar até sexta?"),
    ("claro", "folha_beneficios", "baixa", "Gostaria de saber como incluir meu dependente no plano de saúde na próxima janela de adesão."),
    ("borda", "rede", "alta", "Não consigo entrar no {sistema}. A tela de login nem carrega e a VPN fica desconectando. Hoje não tenho como trabalhar de outro jeito."),
    ("borda", "acesso", "alta", "A VPN conecta normal, mas o {sistema} diz que não tenho permissão para a pasta de {area}. Preciso disso hoje para fechar o mês."),
    ("borda", "equipamento", "media", "O notebook reinicia sozinho e os programas fecham no meio do trabalho. Parece que ele esquenta demais. Às vezes uso a máquina de um colega."),
    ("borda", "software", "critica", "Depois da atualização do {sistema}, os pedidos estão sendo gravados em branco e a equipe de {area} inteira continua lançando. Estamos perdendo dados."),
    ("borda", "acesso", "critica", "Cliquei num link de e-mail estranho e digitei minha senha do {sistema}. Acho que era phishing."),
    ("borda", "instalacoes", "critica", "O ar-condicionado da sala de servidores de {area} parou. A temperatura está subindo e os equipamentos estão desligando."),
    ("borda", "equipamento", "baixa", "oi td bem? n é urgente mas o teclado tá com a tecla E falhando de vez em qnd, da pra ir digitando msm kkk"),
    ("borda", "folha_beneficios", "alta", "Meu pagamento do mês não caiu na conta e tenho o aluguel vencendo hoje."),
]


def gerar_p2(rng):
    casos, gab, fonte = [], {}, {}
    for i, (tipo, cat, urg, modelo) in enumerate(P2_MODELOS, 1):
        slots = {"sistema": rng.choice(SISTEMAS), "area": rng.choice(g1.AREAS), "andar": rng.randint(2, 9),
                 "sala": rng.choice(SALAS), "mes": rng.choice(g1.MESES), "programa": rng.choice(PROGRAMAS)}
        cid = f"S{i:02d}"
        casos.append({"id": cid, "tipo": tipo, "texto": modelo.format(**slots)})
        gab[cid] = {"categoria": cat, "urgencia": urg}
        fonte[cid] = {"modelo": modelo, "slots": slots, "gabarito": gab[cid]}
    return casos, gab, fonte


# ------------------------------------------------------------------ P3: e-mail do que faltou
# padrões de campos faltantes (20 casos). "rel" = prazo relativo no texto; "total" = só valor total no texto.
P3_PADROES = [
    ("completa", []), ("completa", []),
    ("falta_um", ["solicitante_area"]), ("falta_um", ["solicitante_area"]),
    ("falta_um", ["prazo_entrega"]), ("falta_um", ["prazo_entrega"]),
    ("falta_um", ["valor_unitario"]), ("falta_um", ["valor_unitario"]),
    ("falta_um", ["fornecedor"]), ("falta_um", ["fornecedor"]),
    ("falta_dois", ["solicitante_area", "prazo_entrega"]),
    ("falta_dois", ["prazo_entrega", "valor_unitario"]),
    ("falta_dois", ["valor_unitario", "fornecedor"]),
    ("falta_dois", ["solicitante_area", "fornecedor"]),
    ("falta_tres", ["solicitante_area", "prazo_entrega", "valor_unitario"]),
    ("falta_tres", ["prazo_entrega", "valor_unitario", "fornecedor"]),
    ("falta_quatro", ["solicitante_area", "prazo_entrega", "valor_unitario", "fornecedor"]),
    ("prazo_relativo", ["prazo_entrega"]), ("prazo_relativo", ["prazo_entrega", "fornecedor"]),
    ("so_valor_total", []),
]


def gerar_p3(rng):
    casos, gab, fonte = [], {}, {}
    usados = set()
    ordem = list(range(len(P3_PADROES)))
    rng.shuffle(ordem)
    for n, idx in enumerate(ordem, 1):
        tipo, faltam = P3_PADROES[idx]
        rec = g1.registro_base(rng, usados)
        rec["moeda"] = rng.choice(["BRL", "BRL", "USD", "EUR"])
        rec["valor_unitario"] = round(rng.choice([4.5, 12.5, 35, 49.9, 120, 380]), 2)
        total_txt = None
        if tipo == "so_valor_total":
            total = round(rec["valor_unitario"] * rec["quantidade"], 2)
            total_txt = g1.fmt_valor(total, rec["moeda"], "simples")
        for campo in faltam:
            rec[campo] = None
        if tipo == "so_valor_total":
            valor_original = rec["valor_unitario"]
            rec["valor_unitario"] = None  # só para renderizar sem o unitário; o gabarito volta ao original
        if rec["valor_unitario"] is None and tipo != "so_valor_total":
            rec["moeda"] = None
        if tipo == "prazo_relativo":
            rec["_prazo_relativo"] = rng.choice(["daqui 15 dias", "na semana que vem", "em 10 dias úteis"])
        partes, trechos = g1.render(rec, rng, "completa")
        if tipo == "so_valor_total":
            partes.insert(1, f"valor total {total_txt}")
            rec["valor_unitario"] = valor_original
        texto = ". ".join(partes) + "."
        cid = f"E{n:02d}"
        extracao = {k: rec[k] for k in ["solicitante_area", "item", "quantidade", "unidade", "prazo_entrega", "valor_unitario", "moeda", "fornecedor"]}
        casos.append({"id": cid, "tipo": tipo, "texto": texto})
        gab[cid] = {"faltantes": [c for c, _ in pb.P3_CAMPOS if c in faltam], "extracao": extracao}
        fonte[cid] = {"tipo": tipo, "trechos": trechos, "faltam": faltam, "valor_total_texto": total_txt}
    return casos, gab, fonte


# ------------------------------------------------------------------ P4: reclamação
# (tipo, motivo, sentimento, acao, tem_pedido, valor_ou_None, texto com {ped} e {valor})
P4_MODELOS = [
    ("claro", "atraso_entrega", "insatisfeito", "rastrear_pedido", True, None,
     "Meu pedido {ped} deveria ter chegado há duas semanas e até agora nada. Já é a segunda vez que isso acontece e estou bem chateado."),
    ("claro", "atraso_entrega", "neutro", "rastrear_pedido", False, None,
     "Comprei um kit de ferramentas há duas semanas e ele ainda não chegou. Gostaria de saber a previsão."),
    ("claro", "atraso_entrega", "irritado", "rastrear_pedido", True, None,
     "VOCÊS SÃO UMA VERGONHA! Pedido {ped} atrasado de novo, terceira vez este ano!!!"),
    ("claro", "produto_com_defeito", "insatisfeito", "trocar_produto", True, 1899.9,
     "O monitor do pedido {ped} chegou com uma linha verde na tela. Estou decepcionado: paguei R$ {valor} e esperava um produto sem defeito."),
    ("claro", "produto_com_defeito", "neutro", "trocar_produto", False, None,
     "A cadeira que recebi tem um parafuso quebrado no apoio de braço. Como faço para trocar?"),
    ("claro", "produto_com_defeito", "insatisfeito", "reembolsar", True, 249.5,
     "O teclado do pedido {ped} parou de funcionar em três dias. Estou chateado, não quero outro: quero meus R$ {valor} de volta."),
    ("claro", "produto_errado", "insatisfeito", "trocar_produto", True, None,
     "Pedi toner preto no pedido {ped} e veio toner colorido. Fiquei chateado, preciso do correto."),
    ("claro", "produto_errado", "neutro", "trocar_produto", False, None,
     "Recebi papel A5 em vez de A4. Podem enviar o correto?"),
    ("claro", "cobranca_indevida", "insatisfeito", "corrigir_cobranca", True, 380.0,
     "Fui cobrado duas vezes pelo pedido {ped}: R$ {valor} a mais no cartão. Estou insatisfeito."),
    ("claro", "cobranca_indevida", "irritado", "corrigir_cobranca", False, 720.9,
     "ABSURDO! Cobraram R$ {valor} no meu cartão por uma compra que eu cancelei. Quero isso resolvido!!"),
    ("claro", "atendimento", "insatisfeito", "ligar_para_cliente", True, None,
     "Fui transferido quatro vezes no telefone e ninguém resolveu meu problema com o pedido {ped}. Estou frustrado."),
    ("claro", "atendimento", "irritado", "ligar_para_cliente", False, None,
     "O atendente me chamou de burro e desligou na minha cara."),
    ("borda", "indefinido", "neutro", "pedir_mais_informacao", False, None,
     "Oi, tive um problema com a minha compra. Podem me ajudar?"),
    ("borda", "indefinido", "insatisfeito", "pedir_mais_informacao", True, None,
     "Estou muito decepcionado com o pedido {ped}. Não era isso que eu esperava."),
    ("borda", "produto_com_defeito", "irritado", "ligar_para_cliente", True, None,
     "O notebook do pedido {ped} veio com a tela rachada. Se não resolverem em 48 horas vou ao Procon."),
    ("borda", "atraso_entrega", "insatisfeito", "reembolsar", True, 540.0,
     "Pedido {ped} atrasado há 20 dias. Cansei, cancelem e devolvam meus R$ {valor}."),
    ("borda", "cobranca_indevida", "irritado", "ligar_para_cliente", False, 89.9,
     "A fatura veio com R$ {valor} de uma taxa que ninguém me avisou. Vou acionar o Procon se não estornarem."),
    ("borda", "produto_com_defeito", "insatisfeito", "trocar_produto", True, None,
     "O projetor do pedido {ped} queimou com uma semana de uso. Paguei uma fortuna por ele e estou decepcionado."),
    ("borda", "atraso_entrega", "neutro", "rastrear_pedido", False, None,
     "O pedido que termina em 4821 ainda não chegou. Alguém pode ver onde ele está?"),
    ("borda", "produto_errado", "insatisfeito", "trocar_produto", True, None,
     "kkkk bom dia. recebi o item errado denovo, pedido {ped}, mandei a foto. ñ aguento mais isso"),
]


def _br(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_p4(rng):
    casos, gab, fonte = [], {}, {}
    pedidos = rng.sample(range(10000, 99999), N)
    for i, (tipo, motivo, sent, acao, tem_ped, valor, modelo) in enumerate(P4_MODELOS, 1):
        ped = f"PED-{pedidos[i - 1]}"
        texto = modelo.format(ped=ped, valor=_br(valor) if valor is not None else "")
        cid = f"R{i:02d}"
        casos.append({"id": cid, "tipo": tipo, "texto": texto})
        gab[cid] = {"motivo": motivo, "sentimento": sent, "acao_sugerida": acao,
                    "numero_pedido": ped if tem_ped else None, "valor_reclamado": valor}
        fonte[cid] = {"modelo": modelo, "ped": ped, "valor": valor}
    return casos, gab, fonte


# ------------------------------------------------------------------ P5: decisão
def decidir(rec):
    """Regra da política (pb.P5_POLITICA) em código. É a fonte do gabarito do P5."""
    obrig = ["item", "quantidade", "unidade", "prazo_entrega", "valor_unitario", "moeda", "fornecedor"]
    if any(rec[c] is None for c in obrig):
        return "pedir_informacao"
    total = Decimal(str(rec["quantidade"])) * Decimal(str(rec["valor_unitario"])) * pb.CAMBIO[rec["moeda"]]
    if total > pb.LIMITE_BRL or rec["fornecedor"] not in pb.HOMOLOGADOS or rec["item"] in pb.CONTROLADOS:
        return "escalar"
    return "aprovar"


# (tipo, quantidade, valor, moeda, fornecedor, item_controlado, nulls)  fornecedor: "H"=homologado, "N"=não homologado
P5_CASOS = [
    ("aprovar_simples", 10, 35.0, "BRL", "H", False, []),
    ("aprovar_simples", 4, 120.0, "BRL", "H", False, []),
    ("aprovar_usd", 20, 12.5, "USD", "H", False, []),
    ("aprovar_eur", 30, 8.0, "EUR", "H", False, []),
    ("aprovar_no_limite", 10, 500.0, "BRL", "H", False, []),                 # R$ 5.000,00 exato: não escala
    ("aprovar_sem_area", 12, 49.9, "BRL", "H", False, ["solicitante_area"]),    # área é opcional
    ("aprovar_usd_no_limite", 250, 4.0, "USD", "H", False, []),                # 250 x US$ 4 x 5 = 5.000 exato
    ("escalar_acima_do_limite", 10, 500.01, "BRL", "H", False, []),
    ("escalar_usd_converte", 300, 3.5, "USD", "H", False, []),                 # 1.050 numérico, 5.250 em reais
    ("escalar_eur_converte", 900, 1.0, "EUR", "H", False, []),                 # 900 numérico, 5.400 em reais
    ("escalar_fornecedor", 5, 20.0, "BRL", "N", False, []),
    ("escalar_item_controlado", 6, 40.0, "BRL", "H", True, []),
    ("escalar_fornecedor_e_item", 3, 15.0, "BRL", "N", True, []),
    ("escalar_valor_alto_usd", 2, 3000.0, "USD", "H", False, []),
    ("pedir_prazo", 8, 25.0, "BRL", "H", False, ["prazo_entrega"]),
    ("pedir_valor", 15, None, None, "H", False, ["valor_unitario", "moeda"]),
    ("pedir_fornecedor", 10, 60.0, "BRL", "H", False, ["fornecedor"]),
    ("pedir_prazo_e_fornecedor_nao_homologado", 5, 30.0, "BRL", "N", False, ["prazo_entrega"]),   # faltar dado vence
    ("pedir_valor_e_item_controlado", 7, None, None, "H", True, ["valor_unitario", "moeda"]),
    ("pedir_prazo_e_valor_alto", 20, 900.0, "BRL", "H", False, ["prazo_entrega"]),
]


def gerar_p5(rng):
    casos, gab, fonte = [], {}, {}
    itens_livres = [i for i in g1.ITENS if i not in pb.CONTROLADOS]
    nao_homol = [f for f in g1.FORNECEDORES if f not in pb.HOMOLOGADOS]
    ordem = list(range(len(P5_CASOS)))
    rng.shuffle(ordem)
    for n, idx in enumerate(ordem, 1):
        tipo, qtd, val, moeda, forn, controlado, nulls = P5_CASOS[idx]
        item = rng.choice(pb.CONTROLADOS) if controlado else rng.choice(itens_livres)
        rec = {"solicitante_area": rng.choice(g1.AREAS), "item": item, "quantidade": qtd, "unidade": rng.choice(g1.ITENS[item]),
               "prazo_entrega": g1.data_aleatoria(rng), "valor_unitario": val, "moeda": moeda,
               "fornecedor": rng.choice(pb.HOMOLOGADOS) if forn == "H" else rng.choice(nao_homol)}
        for c in nulls:
            rec[c] = None
        cid = f"A{n:02d}"
        casos.append({"id": cid, "tipo": "borda" if any(k in tipo for k in ("no_limite", "converte", "sem_area", "e_item", "e_fornecedor", "e_valor", "acima_do_limite")) else "claro",
                      "subtipo": tipo, "texto": json.dumps(rec, ensure_ascii=False)})
        gab[cid] = {"decisao": decidir(rec)}
        fonte[cid] = {"subtipo": tipo, "registro": rec, "rotulo_pretendido": tipo.split("_")[0]}
    return casos, gab, fonte


# ------------------------------------------------------------------ saída
def escrever(pasta, casos, gab, fonte):
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, obj in [("casos_teste.json", casos), ("gabarito.json", gab), ("registros_fonte.json", fonte)]:
        (pasta / nome).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def gerar_tudo(destino=DADOS):
    resultado = {}
    for nome, fn, off in [("p2", gerar_p2, 0), ("p3", gerar_p3, 1), ("p4", gerar_p4, 2), ("p5", gerar_p5, 3)]:
        rng = random.Random(SEED + off)
        casos, gab, fonte = fn(rng)
        assert len(casos) == N == len(gab), nome
        escrever(destino / nome, casos, gab, fonte)
        resultado[nome] = (casos, gab, fonte)
    return resultado


if __name__ == "__main__":
    r = gerar_tudo()
    print({k: len(v[0]) for k, v in r.items()}, "casos por prompt (seed", SEED, "+ deslocamento por prompt)")
