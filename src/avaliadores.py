"""Regras de acerto de P2 a P5. Escritas ANTES de qualquer rodada paga; não mudam depois de ver resultado.

Cada avaliador recebe (resposta, gabarito, ...) e devolve:
  {"json_valido": bool, "campos": {nome: bool}, "caso_correto": bool, ...extras}

P2  acerto = JSON válido, com as duas chaves e nenhuma a mais, e categoria e urgência iguais ao gabarito.
P3  acerto = o e-mail cita todos os campos que faltam e nenhum que não falta (nome exato do campo, sem acento e
    sem diferença de maiúsculas); se nada falta, a resposta é exatamente NENHUM_CAMPO_FALTANTE. Tom e qualidade
    do texto NÃO entram no acerto (só o formato e o tamanho, como informação à parte).
P4  acerto = JSON válido com as 6 chaves, enums válidos, motivo, sentimento, ação, número do pedido e valor iguais
    ao gabarito (null só igual a null) e resumo de até 20 palavras sem número que não esteja no texto da reclamação.
    "Invenção" = número do pedido ou valor preenchido quando o gabarito é null (contada à parte).
P5  acerto = decisão igual ao gabarito. Com chain-of-thought só o bloco <json> é lido; o raciocínio é ignorado.
"""
import json
import re

import prompts_biblioteca as pb
import validador

CAT = {"acesso", "equipamento", "software", "rede", "instalacoes", "folha_beneficios"}
URG = {"critica", "alta", "media", "baixa"}
MOT = {"atraso_entrega", "produto_com_defeito", "produto_errado", "cobranca_indevida", "atendimento", "indefinido"}
SENT = {"irritado", "insatisfeito", "neutro"}
ACAO = {"rastrear_pedido", "trocar_produto", "reembolsar", "corrigir_cobranca", "ligar_para_cliente", "pedir_mais_informacao"}
DECISAO = {"aprovar", "pedir_informacao", "escalar"}
MAX_PALAVRAS_RESUMO = 20
MAX_PALAVRAS_EMAIL = 120


def _numero(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _parse(resposta, cot=False):
    return validador.parse(resposta, "T3" if cot else "T1")


def avaliar_p2(resposta, gab, texto=None):
    obj, ok = _parse(resposta)
    campos = {"categoria": False, "urgencia": False}
    chaves_ok = ok and set(obj) == {"categoria", "urgencia"}
    if chaves_ok:
        campos["categoria"] = obj["categoria"] == gab["categoria"] and obj["categoria"] in CAT
        campos["urgencia"] = obj["urgencia"] == gab["urgencia"] and obj["urgencia"] in URG
    return {"json_valido": ok, "campos": campos, "caso_correto": chaves_ok and all(campos.values())}


def _norm(s):
    return validador.norm_texto(s)


ROTULOS_P3 = {campo: _norm(rotulo) for campo, rotulo in pb.P3_CAMPOS}


def campos_citados(email):
    t = _norm(email)
    return {campo for campo, rot in ROTULOS_P3.items() if rot in t}


def avaliar_p3(resposta, gab, texto=None):
    esperado = set(gab["faltantes"])
    sentinela = resposta.strip() == pb.P3_SENTINELA
    citados = set() if sentinela else campos_citados(resposta)
    if not esperado:
        correto = sentinela
    else:
        correto = (not sentinela) and citados == esperado
    corpo = resposta.strip().split("\n", 1)
    palavras = len(corpo[1].split()) if len(corpo) > 1 else 0
    formato_ok = (not esperado and sentinela) or (resposta.lstrip().startswith("Assunto:") and 0 < palavras <= MAX_PALAVRAS_EMAIL)
    return {"json_valido": True,  # não se aplica; mantido para as tabelas terem as mesmas colunas
            "campos": {c: (c in citados) == (c in esperado) for c, _ in pb.P3_CAMPOS},
            "caso_correto": correto,
            "citados": sorted(citados), "esperados": sorted(esperado),
            "faltou_citar": sorted(esperado - citados), "citou_a_mais": sorted(citados - esperado),
            "formato_ok": bool(formato_ok), "palavras_corpo": palavras}


def _numeros_do_texto(t):
    return set(re.findall(r"\d+", t))


def avaliar_p4(resposta, gab, texto=""):
    obj, ok = _parse(resposta)
    nomes = ["resumo", "motivo", "sentimento", "acao_sugerida", "numero_pedido", "valor_reclamado"]
    campos = {n: False for n in nomes}
    invencoes = 0
    chaves_ok = ok and set(obj) == set(nomes)
    if chaves_ok:
        campos["motivo"] = obj["motivo"] in MOT and obj["motivo"] == gab["motivo"]
        campos["sentimento"] = obj["sentimento"] in SENT and obj["sentimento"] == gab["sentimento"]
        campos["acao_sugerida"] = obj["acao_sugerida"] in ACAO and obj["acao_sugerida"] == gab["acao_sugerida"]
        np_, gp = obj["numero_pedido"], gab["numero_pedido"]
        campos["numero_pedido"] = (np_ is None and gp is None) or (isinstance(np_, str) and np_ == gp)
        vr, gv = obj["valor_reclamado"], gab["valor_reclamado"]
        campos["valor_reclamado"] = (vr is None and gv is None) or (_numero(vr) and gv is not None and float(vr) == float(gv))
        r = obj["resumo"]
        campos["resumo"] = isinstance(r, str) and 0 < len(r.split()) <= MAX_PALAVRAS_RESUMO and _numeros_do_texto(r) <= _numeros_do_texto(texto)
        invencoes = int(gab["numero_pedido"] is None and np_ is not None) + int(gab["valor_reclamado"] is None and vr is not None)
    return {"json_valido": ok, "campos": campos, "caso_correto": chaves_ok and all(campos.values()), "invencoes": invencoes}


def avaliar_p5(resposta, gab, texto=None, cot=False):
    obj, ok = _parse(resposta, cot)
    chaves_ok = ok and set(obj) == {"decisao", "motivo"}
    campos = {"decisao": bool(chaves_ok and obj["decisao"] in DECISAO and obj["decisao"] == gab["decisao"])}
    return {"json_valido": ok, "campos": campos, "caso_correto": chaves_ok and campos["decisao"]}


AVALIADORES = {"p2": avaliar_p2, "p3": avaliar_p3, "p4": avaliar_p4, "p5": avaliar_p5}


def avaliar(dados, resposta, gab, texto="", cot=False):
    if dados == "p5":
        return avaliar_p5(resposta, gab, texto, cot=cot)
    return AVALIADORES[dados](resposta, gab, texto)
