"""Diagnóstico dos erros das rodadas novas, feito DEPOIS da medição e sem chamar a API.

Entrada: respostas gravadas em resultados/biblioteca/brutos/ e os gabaritos congelados.
Saída: resultados/biblioteca/diagnostico.json e DIAGNOSTICO.md (gerados; nenhum número digitado à mão).

Importante: as regras de acerto oficiais (src/avaliadores.py) NÃO mudam. A "reanálise por pedido" abaixo é uma regra
auxiliar, escrita depois de ler os erros, e serve só para explicar o resultado do P3 e do E4. Ela não substitui o acerto
medido e vem sempre rotulada como reanálise.

Regra auxiliar do P3 ("pedido"): um campo conta como PEDIDO no e-mail quando seu nome aparece em um item de lista
(linha iniciada por "-", "•", "*" ou "1." / "1)"); o nome aparecendo só em frase corrida (por exemplo, "com fornecedor X",
"o prazo já consta") conta como MENÇÃO, isto é, o e-mail confirma um dado recebido sem pedi-lo de novo.
"""
import json
import math
import re
from collections import Counter
from pathlib import Path

import analisar_biblioteca as ab
import avaliadores as av
import experimentos as ex
import prompts_biblioteca as pb

RAIZ = Path(__file__).resolve().parent.parent
SAIDA_JSON = RAIZ / "resultados" / "biblioteca" / "diagnostico.json"
SAIDA_MD = RAIZ / "resultados" / "biblioteca" / "DIAGNOSTICO.md"
ITEM_LISTA = re.compile(r"^\s*(?:[-•*]|\d+[.)])\s+")
ROTULO = dict(pb.P3_CAMPOS)


def _json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _linhas_lista(email):
    return [av._norm(l) for l in email.splitlines() if ITEM_LISTA.match(l)]


def campos_pedidos(email):
    """Campos cujo nome aparece em item de lista (pedido). Os demais citados são menções."""
    itens = _linhas_lista(email)
    return {c for c, rot in av.ROTULOS_P3.items() if any(rot in l for l in itens)}


def _extracao_certa(etapa1, gab_extracao):
    obj, ok = av._parse(etapa1)
    if not ok:
        return False
    return all(obj.get(k) == v for k, v in gab_extracao.items())


def classificar_resposta_p3(r, gab):
    a = r["avaliacao"]
    esperado = set(gab["faltantes"])
    citados = set(a["citados"])
    pedidos = campos_pedidos(r["resposta"]) if "Assunto:" in r["resposta"] else set()
    pediu_a_mais = sorted(pedidos - esperado)
    so_mencionou = sorted((citados - esperado) - set(pediu_a_mais))
    faltou = sorted(esperado - citados)
    if a["caso_correto"]:
        classe = "correta"
    elif faltou:
        classe = "esqueceu_campo"
    elif pediu_a_mais:
        classe = "pediu_campo_que_ja_tinha"
    else:
        classe = "so_confirmou_dado_recebido"
    return {"classe": classe, "pediu_a_mais": pediu_a_mais, "so_mencionou": so_mencionou, "faltou": faltou,
            "correta_por_pedido": not faltou and not pediu_a_mais}


def diagnostico_e4(pasta_brutos=ex.BRUTOS, raiz=RAIZ):
    gab = _json(raiz / "dados" / "biblioteca" / "p3" / "gabarito.json")
    casos = {c["id"]: c for c in _json(raiz / "dados" / "biblioteca" / "p3" / "casos_teste.json")}
    saida = {}
    for v in ("encadeado", "unico"):
        regs = [json.loads(l) for l in (Path(pasta_brutos) / f"E4_{v}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        n = len(regs)
        erradas = [r for r in regs if not r["avaliacao"]["caso_correto"]]
        classes = Counter()
        por_campo_pedido, por_campo_mencao = Counter(), Counter()
        extracao_errada = 0
        area_compras = 0
        por_caso_pedido = {}
        for r in erradas:
            c = classificar_resposta_p3(r, gab[r["caso"]])
            classes[c["classe"]] += 1
            por_campo_pedido.update(c["pediu_a_mais"])
            por_campo_mencao.update(c["so_mencionou"])
            if v == "encadeado" and not _extracao_certa(r["etapas"][0]["resposta"], gab[r["caso"]]["extracao"]):
                extracao_errada += 1
            if "solicitante_area" in c["pediu_a_mais"] and gab[r["caso"]]["extracao"]["solicitante_area"] == "Compras":
                area_compras += 1
            if c["pediu_a_mais"]:
                por_caso_pedido.setdefault(r["caso"], 0)
                por_caso_pedido[r["caso"]] += 1
        # acerto pela regra auxiliar (por caso, média das repetições, como no oficial)
        por_caso = {}
        for r in regs:
            por_caso.setdefault(r["caso"], []).append(1.0 if classificar_resposta_p3(r, gab[r["caso"]])["correta_por_pedido"] else 0.0)
        acerto_pedido = math.fsum(math.fsum(x) / len(x) for x in por_caso.values()) / len(por_caso)
        saida[v] = {"respostas": n, "erradas": len(erradas), "classes": dict(classes), "pediu_a_mais_por_campo": dict(por_campo_pedido),
                    "so_mencionou_por_campo": dict(por_campo_mencao), "extracao_p1_errada_nas_erradas": extracao_errada if v == "encadeado" else None,
                    "pediu_area_compras": area_compras, "casos_com_pedido_a_mais": por_caso_pedido,
                    "acerto_pedido": acerto_pedido, "acerto_oficial": ab.resumir_variante(regs)["acerto_caso_media"]}
    saida["extracao_p1_certa_em_todas"] = None
    # extração do P1 em todas as respostas do encadeado (não só nas erradas)
    regs = [json.loads(l) for l in (Path(pasta_brutos) / "E4_encadeado.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    saida["extracao_p1_certa_em_todas"] = {"certas": sum(_extracao_certa(r["etapas"][0]["resposta"], gab[r["caso"]]["extracao"]) for r in regs), "de": len(regs)}
    return saida


def _lista_erros(arquivo, dados, ordem_campos=None):
    regs = [json.loads(l) for l in Path(arquivo).read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in regs if not r["avaliacao"]["caso_correto"]], len(regs)


def diagnostico_e3(pasta_brutos=ex.BRUTOS, raiz=RAIZ):
    gab = _json(raiz / "dados" / "biblioteca" / "p2" / "gabarito.json")
    casos = {c["id"]: c for c in _json(raiz / "dados" / "biblioteca" / "p2" / "casos_teste.json")}
    saida = {}
    for v in ("zero_shot", "few_shot"):
        erradas, n = _lista_erros(Path(pasta_brutos) / f"E3_{v}.jsonl", None)
        campo = Counter()
        pares = Counter()
        com_prazo = 0
        for r in erradas:
            obj, _ = av._parse(r["resposta"])
            g = gab[r["caso"]]
            for k in ("categoria", "urgencia"):
                if obj.get(k) != g[k]:
                    campo[k] += 1
            if obj.get("urgencia") != g["urgencia"]:
                pares[(g["urgencia"], obj.get("urgencia"))] += 1
            if re.search(r"até|ate |hoje|amanhã|sexta|segunda|fim da semana|vencendo", casos[r["caso"]]["texto"], re.I):
                com_prazo += 1
        saida[v] = {"respostas": n, "erradas": len(erradas), "campo_errado": dict(campo),
                    "urgencia_esperada_obtida": [{"esperada": a, "obtida": b, "n": k} for (a, b), k in pares.most_common()],
                    "erradas_em_casos_com_prazo_no_texto": com_prazo, "casos": sorted({r["caso"] for r in erradas})}
    return saida


def diagnostico_p4(pasta_brutos=ex.BRUTOS, raiz=RAIZ):
    gab = _json(raiz / "dados" / "biblioteca" / "p4" / "gabarito.json")
    erradas, n = _lista_erros(Path(pasta_brutos) / "P4_saida_estruturada.jsonl", None)
    campo, pares = Counter(), Counter()
    for r in erradas:
        for k, ok in r["avaliacao"]["campos"].items():
            if not ok:
                campo[k] += 1
        obj, _ = av._parse(r["resposta"])
        g = gab[r["caso"]]
        if obj.get("sentimento") != g["sentimento"]:
            pares[(g["sentimento"], obj.get("sentimento"))] += 1
    regs = [json.loads(l) for l in (Path(pasta_brutos) / "P4_saida_estruturada.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return {"respostas": n, "erradas": len(erradas), "campo_errado": dict(campo),
            "sentimento_esperado_obtido": [{"esperado": a, "obtido": b, "n": k} for (a, b), k in pares.most_common()],
            "invencoes": sum(r["avaliacao"]["invencoes"] for r in regs), "casos": sorted({r["caso"] for r in erradas})}


def diagnostico_e5(pasta_brutos=ex.BRUTOS, raiz=RAIZ):
    gab = _json(raiz / "dados" / "biblioteca" / "p5" / "gabarito.json")
    casos = {c["id"]: c for c in _json(raiz / "dados" / "biblioteca" / "p5" / "casos_teste.json")}
    saida = {}
    for v in ("direto", "cot"):
        erradas, n = _lista_erros(Path(pasta_brutos) / f"E5_{v}.jsonl", None)
        pares = Counter()
        duplas = 0
        for r in erradas:
            decs = re.findall(r'"decisao":\s*"(\w+)"', r["resposta"])
            if len(decs) > 1:       # duas decisões na mesma saída (o modelo se corrigiu no meio): o código não consegue ler
                duplas += 1
                obtida = "duas respostas (" + " → ".join(decs) + ")"
            else:
                obtida = decs[0] if decs else "ilegível"
            pares[(r["caso"], casos[r["caso"]]["subtipo"], gab[r["caso"]]["decisao"], obtida)] += 1
        saida[v] = {"respostas": n, "erradas": len(erradas), "com_duas_decisoes": duplas,
                    "erros": [{"caso": c, "subtipo": s, "esperada": e, "obtida": o, "n": k} for (c, s, e, o), k in sorted(pares.items())]}
    return saida


def construir(pasta_brutos=ex.BRUTOS, raiz=RAIZ):
    return {"E4": diagnostico_e4(pasta_brutos, raiz), "E3": diagnostico_e3(pasta_brutos, raiz), "P4": diagnostico_p4(pasta_brutos, raiz),
            "E5": diagnostico_e5(pasta_brutos, raiz)}


def _pct(x):
    return ab.pct(x)


def relatorio(d):
    e4, e3, p4 = d["E4"], d["E3"], d["P4"]
    L = ["# Diagnóstico dos erros (feito depois da medição, sem chamar a API)", "",
         "Gerado por `python src/diagnostico.py` a partir de `resultados/biblioteca/brutos/`. As regras de acerto oficiais não mudaram; "
         "a \"reanálise por pedido\" do P3 é uma regra auxiliar, escrita depois de ler os erros, e só serve para explicar o resultado (veja o docstring do script).", "",
         "## P3 / E4: por que o acerto foi o menor", "",
         f"Extração do P1 correta (os 8 campos iguais ao gabarito) em {e4['extracao_p1_certa_em_todas']['certas']} de {e4['extracao_p1_certa_em_todas']['de']} respostas do fluxo encadeado.", "",
         "| Fluxo | Respostas | Erradas (oficial) | Pediu campo que já tinha | Só confirmou dado recebido | Esqueceu campo | Acerto oficial | Acerto pela reanálise por pedido |", "|---|---|---|---|---|---|---|---|"]
    for v, rot in (("encadeado", "Encadeado (P1 → P3)"), ("unico", "Prompt único")):
        x = e4[v]
        c = x["classes"]
        L.append(f"| {rot} | {x['respostas']} | {x['erradas']} | {c.get('pediu_campo_que_ja_tinha', 0)} | {c.get('so_confirmou_dado_recebido', 0)} | {c.get('esqueceu_campo', 0)} | {_pct(x['acerto_oficial'])} | {_pct(x['acerto_pedido'])} |")
    L += ["", f"Erros do encadeado em que a extração do P1 estava errada: {e4['encadeado']['extracao_p1_errada_nas_erradas']} de {e4['encadeado']['erradas']}.",
          f"Erros do prompt único em que o e-mail pediu a área solicitante e a área era \"Compras\": {e4['unico']['pediu_area_compras']} de {e4['unico']['erradas']}.", "",
          "## E3: onde o zero-shot errou", "", "| Variante | Respostas | Erradas | Campo errado | Urgência esperada → obtida |", "|---|---|---|---|---|"]
    for v, rot in (("zero_shot", "Zero-shot"), ("few_shot", "Few-shot")):
        x = e3[v]
        campos = ", ".join(f"{k}: {n}" for k, n in x["campo_errado"].items()) or "—"
        trocas = "; ".join("{} → {} ({})".format(t["esperada"], t["obtida"], t["n"]) for t in x["urgencia_esperada_obtida"]) or "—"
        L.append(f"| {rot} | {x['respostas']} | {x['erradas']} | {campos} | {trocas} |")
    e5 = d["E5"]
    L += ["", "## E5: onde a resposta direta errou", "", "| Variante | Respostas | Erradas | Erros (caso, tipo, esperada → obtida, vezes) |", "|---|---|---|---|"]
    for v, rot in (("direto", "Sem raciocínio"), ("cot", "Com raciocínio")):
        x = e5[v]
        erros = "; ".join("{} ({}), {} → {}, {}x".format(t["caso"], t["subtipo"], t["esperada"], t["obtida"], t["n"]) for t in x["erros"]) or "—"
        L.append(f"| {rot} | {x['respostas']} | {x['erradas']} | {erros} |")
    campos4 = ", ".join(f"{k}: {n}" for k, n in p4["campo_errado"].items())
    trocas4 = "; ".join("{} → {} ({})".format(t["esperado"], t["obtido"], t["n"]) for t in p4["sentimento_esperado_obtido"])
    L += ["", "## P4: onde errou", "", f"{p4['erradas']} de {p4['respostas']} respostas erradas; campo errado: {campos4}. "
          f"Sentimento esperado → obtido: {trocas4}. Invenções de número ou valor: {p4['invencoes']}.", ""]
    return "\n".join(L)


def main():
    d = construir()
    SAIDA_JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    SAIDA_MD.write_text(relatorio(d), encoding="utf-8", newline="\n")
    print(relatorio(d))


if __name__ == "__main__":
    main()
