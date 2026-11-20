"""Valida os dados de P2 a P5 relendo cada texto de forma independente do gerador, e congela por hash.

  python src/validar_dados_biblioteca.py            # valida
  python src/validar_dados_biblioteca.py --congelar # valida e grava CONGELADO.sha256 em cada pasta

A validação NÃO usa os modelos de texto do gerador: lê o texto pronto com regex e compara com o gabarito.
O que ela não consegue conferir (por exemplo, se o "certo" de um caso ambíguo é o mais sensato) fica para
a revisão manual, registrada em dados/biblioteca/REVISAO_E_LIMITACOES.md.
"""
import hashlib
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

import gerar_dados as g1
import prompts_biblioteca as pb

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados" / "biblioteca"
ARQUIVOS_CONGELADOS = ["casos_teste.json", "gabarito.json"]

CATEGORIAS = {"acesso", "equipamento", "software", "rede", "instalacoes", "folha_beneficios"}
URGENCIAS = {"critica", "alta", "media", "baixa"}
MOTIVOS = {"atraso_entrega", "produto_com_defeito", "produto_errado", "cobranca_indevida", "atendimento", "indefinido"}
SENTIMENTOS = {"irritado", "insatisfeito", "neutro"}
ACOES = {"rastrear_pedido", "trocar_produto", "reembolsar", "corrigir_cobranca", "ligar_para_cliente", "pedir_mais_informacao"}
NOMES_REAIS_PROIBIDOS = ["ifood", "amazon", "google", "microsoft", "petrobras", "magazine luiza", "mercado livre", "kabum", "americanas"]
EMOCAO = ["chateado", "decepcionad", "frustrad", "cansei", "cansad", "insatisfeit", "aguento"]


def _ler(pasta):
    return (json.loads((pasta / "casos_teste.json").read_text(encoding="utf-8")),
            json.loads((pasta / "gabarito.json").read_text(encoding="utf-8")))


def _comuns(nome, casos, gab, erros):
    ids = [c["id"] for c in casos]
    if len(casos) != 20:
        erros.append(f"{nome}: {len(casos)} casos (esperado 20)")
    if len(set(ids)) != len(ids) or set(ids) != set(gab):
        erros.append(f"{nome}: ids duplicados ou gabarito com ids diferentes")
    if len({c["texto"] for c in casos}) != len(casos):
        erros.append(f"{nome}: textos duplicados")
    for c in casos:
        if re.search(r"[{}]", c["texto"]) and nome != "p5":
            erros.append(f"{nome} {c['id']}: marcador sem preencher no texto")
        if any(x in c["texto"].lower() for x in NOMES_REAIS_PROIBIDOS):
            erros.append(f"{nome} {c['id']}: nome de empresa real na lista de proibidos")
    if sum(c["tipo"] == "borda" for c in casos) < 3 and nome in {"p2", "p4", "p5"}:
        erros.append(f"{nome}: poucos casos de borda")


def validar_p2(casos, gab, erros):
    _comuns("p2", casos, gab, erros)
    for c in casos:
        g = gab[c["id"]]
        if g["categoria"] not in CATEGORIAS or g["urgencia"] not in URGENCIAS:
            erros.append(f"p2 {c['id']}: valor fora do enum")
    if {g["categoria"] for g in gab.values()} != CATEGORIAS:
        erros.append("p2: alguma categoria sem caso de teste")
    if {g["urgencia"] for g in gab.values()} != URGENCIAS:
        erros.append("p2: algum nível de urgência sem caso de teste")
    textos_fs = {e["entrada"] for e in pb.EXEMPLOS_P2}
    if any(c["texto"] in textos_fs for c in casos):
        erros.append("p2: caso de teste repete um exemplo do few-shot")
    # regra de urgência escrita no prompt: "critica" só com área inteira parada ou segurança de pessoas/dados
    gatilho = r"equipe|inteir|gás|phishing|perdendo dados|sala de servidores"
    palavras = {"acesso": r"acesso|senha|conta|permiss", "equipamento": r"notebook|mouse|teclado|monitor|impressora",
                "software": r"sistema|programa|editor|atualiz", "rede": r"internet|wi-fi|vpn",
                "instalacoes": r"lâmpada|gás|ar-condicionado|cadeira", "folha_beneficios": r"holerite|plano de saúde|pagamento|vale-refeição"}
    for c in casos:
        t = c["texto"].lower()
        g = gab[c["id"]]
        if (g["urgencia"] == "critica") != bool(re.search(gatilho, t)):
            erros.append(f"p2 {c['id']}: urgência crítica e gatilho da definição (área inteira, segurança, perda de dados) não coincidem")
        if c["tipo"] == "claro" and not re.search(palavras[g["categoria"]], t):
            erros.append(f"p2 {c['id']}: caso claro sem nenhuma palavra típica da categoria {g['categoria']}")


_RE_DATA = re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{1,2} de \w+ de \d{4}|\d{2}-\w{3}-\d{4}")


def validar_p3(casos, gab, erros):
    _comuns("p3", casos, gab, erros)
    forn = list(g1.FORNECEDORES)
    for c in casos:
        t, g = c["texto"], gab[c["id"]]
        lidos = set()
        if not re.search(r"solicitante:|para a área de", t):
            lidos.add("solicitante_area")
        if not _RE_DATA.search(t):
            lidos.add("prazo_entrega")
        if not re.search(r"R\$|US\$|€", t):
            lidos.add("valor_unitario")
        if not any(f in t for f in forn):
            lidos.add("fornecedor")
        esperado = {k for k in ("solicitante_area", "prazo_entrega", "valor_unitario", "fornecedor") if g["extracao"][k] is None}
        if set(g["faltantes"]) != esperado:
            erros.append(f"p3 {c['id']}: faltantes diferem dos campos null da extração")
        if lidos != set(g["faltantes"]):
            erros.append(f"p3 {c['id']}: leitura independente do texto diz faltar {sorted(lidos)}, gabarito diz {g['faltantes']}")
        if "valor total" in t:
            qtd, total = g["extracao"]["quantidade"], re.search(r"valor total \S+ ([\d.,]+)", t)
            v = float(total.group(1).replace(".", "").replace(",", "."))
            if abs(v / qtd - g["extracao"]["valor_unitario"]) > 0.005:
                erros.append(f"p3 {c['id']}: valor total / quantidade não bate com o valor_unitario do gabarito")
    padroes = {len(g["faltantes"]) for g in gab.values()}
    if not {0, 1, 2, 3, 4} <= padroes:
        erros.append("p3: faltam casos com 0, 1, 2, 3 e 4 campos faltantes")


def validar_p4(casos, gab, erros):
    _comuns("p4", casos, gab, erros)
    for c in casos:
        t, g = c["texto"], gab[c["id"]]
        if g["motivo"] not in MOTIVOS or g["sentimento"] not in SENTIMENTOS or g["acao_sugerida"] not in ACOES:
            erros.append(f"p4 {c['id']}: valor fora do enum")
        m = re.search(r"PED-\d{5}", t)
        if (m.group(0) if m else None) != g["numero_pedido"]:
            erros.append(f"p4 {c['id']}: numero_pedido do gabarito difere do que está escrito no texto")
        v = re.search(r"R\$ ([\d.]+,\d{2})", t)
        val = float(v.group(1).replace(".", "").replace(",", ".")) if v else None
        if val != g["valor_reclamado"]:
            erros.append(f"p4 {c['id']}: valor_reclamado do gabarito difere do que está escrito no texto")
        irritado = bool(re.search(r"\b[A-ZÁÂÃÉÊÍÓÔÕÚÇ]{5,}\b", t)) or "procon" in t.lower() or "burro" in t.lower()
        emocao = any(e in t.lower() for e in EMOCAO)
        esperado_sent = "irritado" if irritado else "insatisfeito" if emocao else "neutro"
        if g["sentimento"] != esperado_sent:
            erros.append(f"p4 {c['id']}: sentimento do gabarito ({g['sentimento']}) difere da regra do prompt aplicada ao texto ({esperado_sent})")
        procon = "procon" in t.lower()
        volta = bool(re.search(r"de volta|devolvam", t.lower()))
        tabela = {"atraso_entrega": "rastrear_pedido", "produto_com_defeito": "trocar_produto", "produto_errado": "trocar_produto",
                  "cobranca_indevida": "corrigir_cobranca", "atendimento": "ligar_para_cliente", "indefinido": "pedir_mais_informacao"}
        acao = "ligar_para_cliente" if procon else "reembolsar" if volta else tabela[g["motivo"]]
        if g["acao_sugerida"] != acao:
            erros.append(f"p4 {c['id']}: ação do gabarito difere da regra do prompt aplicada ao motivo ({acao})")
    if sum(g["numero_pedido"] is None for g in gab.values()) < 5 or sum(g["valor_reclamado"] is None for g in gab.values()) < 8:
        erros.append("p4: poucos casos em que numero_pedido e valor_reclamado devem ser null (o teste de não inventar fica fraco)")


def decidir_independente(rec):
    """Segunda implementação da política do P5, com frações exatas (a do gerador usa Decimal)."""
    if any(rec[c] is None for c in ("item", "quantidade", "unidade", "prazo_entrega", "valor_unitario", "moeda", "fornecedor")):
        return "pedir_informacao"
    total = Fraction(str(rec["quantidade"])) * Fraction(str(rec["valor_unitario"])) * pb.CAMBIO[rec["moeda"]]
    motivos = [total > pb.LIMITE_BRL, rec["fornecedor"] not in pb.HOMOLOGADOS, rec["item"] in pb.CONTROLADOS]
    return "escalar" if any(motivos) else "aprovar"


def validar_p5(casos, gab, erros):
    _comuns("p5", casos, gab, erros)
    cont = {}
    for c in casos:
        rec = json.loads(c["texto"])
        d = decidir_independente(rec)
        cont[d] = cont.get(d, 0) + 1
        if gab[c["id"]]["decisao"] != d:
            erros.append(f"p5 {c['id']}: gabarito {gab[c['id']]['decisao']} difere da recontagem independente {d}")
    if min(cont.get(k, 0) for k in ("aprovar", "pedir_informacao", "escalar")) < 5:
        erros.append(f"p5: classes desbalanceadas {cont}")
    sub = {c["subtipo"] for c in casos}
    for exigido in ("aprovar_no_limite", "aprovar_usd_no_limite", "escalar_usd_converte", "escalar_eur_converte", "pedir_prazo_e_fornecedor_nao_homologado"):
        if exigido not in sub:
            erros.append(f"p5: caso de borda ausente: {exigido}")


VALIDADORES = {"p2": validar_p2, "p3": validar_p3, "p4": validar_p4, "p5": validar_p5}


def validar(dados=DADOS):
    erros = []
    for nome, fn in VALIDADORES.items():
        casos, gab = _ler(dados / nome)
        fn(casos, gab, erros)
    return erros


def hashes(pasta):
    return {a: hashlib.sha256((pasta / a).read_bytes()).hexdigest() for a in ARQUIVOS_CONGELADOS}


def congelar(dados=DADOS):
    for nome in VALIDADORES:
        h = hashes(dados / nome)
        (dados / nome / "CONGELADO.sha256").write_text("".join(f"{v}  {k}\n" for k, v in h.items()), encoding="utf-8", newline="\n")


def conferir_congelamento(dados=DADOS):
    """-> lista de arquivos cujo hash não bate com CONGELADO.sha256."""
    ruins = []
    for nome in VALIDADORES:
        arq = dados / nome / "CONGELADO.sha256"
        if not arq.exists():
            ruins.append(f"{nome}: sem CONGELADO.sha256")
            continue
        esperado = dict(reversed(l.split("  ", 1)) for l in arq.read_text(encoding="utf-8").splitlines() if l)
        atual = hashes(dados / nome)
        ruins += [f"{nome}/{k}" for k in ARQUIVOS_CONGELADOS if esperado.get(k) != atual[k]]
    return ruins


if __name__ == "__main__":
    e = validar()
    for x in e:
        print("ERRO:", x)
    if e:
        sys.exit(1)
    print("Validação independente: 80 casos, 0 divergências.")
    if "--congelar" in sys.argv:
        congelar()
        print("Congelado (CONGELADO.sha256 em cada pasta).")
