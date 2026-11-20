"""Monta resultados/resumo.json: o arquivo único que alimenta a demo (docs/index.html) e o README.

Fontes (todas versionadas):
  resultados/extracao/v2/resumo.json, iteracao.json, respostas_gravadas.json   E1 e E2 (já medidos, não reescritos)
  resultados/biblioteca/brutos/*.jsonl, piloto/                                E3, E4, E5 e P4 (rodadas novas)
  prompts/*.json, prompts/extracao/*.json, dados/                              textos dos prompts e casos

Nenhum número é digitado à mão: as frases de resultado são montadas aqui, a partir dos arquivos acima. O que não foi
medido aparece com "medido": false e o comando para medir. Uso: python src/consolidar.py
"""
import difflib
import json
from pathlib import Path

import analisar_biblioteca as ab
import conteudo_biblioteca as cb
import experimentos as ex
import prompts_biblioteca as pb
import prompts_lib as pl

RAIZ = Path(__file__).resolve().parent.parent
EXT_V2 = RAIZ / "resultados" / "extracao" / "v2"
EXT_V1 = RAIZ / "resultados" / "extracao" / "v1"
SAIDA = RAIZ / "resultados" / "resumo.json"
GASTO_DETALHE = [  # livro-caixa das rodadas anteriores (README original, seção 7.4; conferido contra os resumos)
    {"rodada": "Extração v1 (piloto de 10 chamadas e 600 respostas)", "usd": 0.107289},
    {"rodada": "Extração v2 (600 respostas)", "usd": 0.119941},
    {"rodada": "Iteração do T4 (150 respostas)", "usd": 0.021739},
]
NOMES_TEC = {"T1": "Zero-shot", "T2": "Few-shot", "T3": "Chain-of-thought", "T4": "System prompt"}


# ------------------------------------------------------------------ formatação
def br(x, casas=1):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, casas=1):
    return br(x * 100, casas) + "%"


def usd(x, casas=6):
    return "US$ " + br(x, casas)


def _json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ E1 e E2
def montar_e1(resumo_v2, casos_v2):
    ids = sorted(resumo_v2["T1"]["acerto_por_caso"])
    todos_certos = [c for c in ids if all(resumo_v2[t]["acerto_por_caso"][c] == 1.0 for t in NOMES_TEC)]
    tipos = {c["id"]: c["tipo"] for c in casos_v2}
    casos_vt = [c for c in ids if tipos[c] == "valor_total"]
    reps = resumo_v2["T1"]["repeticoes"]
    n_resp_vt = len(casos_vt) * reps
    por_tec = {}
    for t in NOMES_TEC:
        r = resumo_v2[t]
        certas_vt = round(sum(r["acerto_por_caso"][c] for c in casos_vt) * reps)
        por_tec[t] = {"rotulo": NOMES_TEC[t], "hash12": r["prompt_hash12"], "acerto": r["acerto_caso_media"], "custo_resposta_usd": r["custo_por_caso_usd"],
                      "latencia_media_s": r["latencia_media_s"], "certas_valor_total": certas_vt, "respostas_valor_total": n_resp_vt,
                      "ic95": [r["ic95_baixo"], r["ic95_alto"]], "rep_min": r["acerto_caso_rep_min"], "rep_max": r["acerto_caso_rep_max"]}
    t1, t3 = resumo_v2["T1"], resumo_v2["T3"]
    razao = t3["custo_por_caso_usd"] / t1["custo_por_caso_usd"]
    outros = [c for c in ids if c not in casos_vt]
    assert all(c in todos_certos for c in outros), "esperado: todas as técnicas acertam todos os casos fora do tipo valor_total"
    resultado = (f"Em {len(todos_certos)} de {len(ids)} casos todas as técnicas acertaram; a diferença apareceu só quando a regra de negócio "
                 f"(calcular o valor unitário a partir do total) não estava escrita no prompt.")
    quando = (f"Em extração simples, comece pelo prompt mais barato e escreva as regras de negócio dentro dele. O raciocínio passo a passo custou "
              f"{br(razao)} vezes mais por resposta que o zero-shot; a vantagem numérica dele apareceu só onde havia cálculo implícito, e esse caso a regra escrita resolveu (Experimento 2).")
    barras_acerto = [{"rotulo": v["rotulo"], "valor": v["acerto"], "texto": pct(v["acerto"]), "sub": f"{usd(v['custo_resposta_usd'])} por resposta"} for v in por_tec.values()]
    barras_vt = [{"rotulo": v["rotulo"], "valor": v["certas_valor_total"] / n_resp_vt, "texto": f"{v['certas_valor_total']}/{n_resp_vt}", "sub": ""} for v in por_tec.values()]
    return {"id": "E1", **cb.EXPERIMENTOS["E1"], "o_que_testei": f"4 técnicas de prompt (zero-shot, few-shot, chain-of-thought e system prompt) nos mesmos {len(ids)} pedidos fictícios, {reps} repetições cada.",
            "medido": True, "status": "medido", "resultado": resultado, "numero": f"{pct(min(v['acerto'] for v in por_tec.values()))} a {pct(max(v['acerto'] for v in por_tec.values()))} de acerto, conforme a técnica; {len(todos_certos)} de {len(ids)} casos sem nenhuma diferença",
            "grupos": [{"titulo": "Acerto por técnica (50 casos × 3 repetições)", "barras": barras_acerto},
                       {"titulo": f"Só no tipo \"valor total\" ({len(casos_vt)} casos, {n_resp_vt} respostas por técnica)", "barras": barras_vt}],
            "quando_usar": quando, "tecnicas": por_tec, "casos_sem_diferenca": len(todos_certos), "casos_total": len(ids), "casos_valor_total": len(casos_vt)}


def diff_prompts(v1, v2):
    """Diff linha a linha do system prompt T4 v1 → v2, com 1 linha de contexto. -> lista de {tipo, texto}."""
    a, b = v1["system"].splitlines(), v2["system"].splitlines()
    saida = []
    for linha in difflib.unified_diff(a, b, lineterm="", n=1):
        if linha.startswith(("---", "+++")):
            continue
        if linha.startswith("@@"):
            saida.append({"tipo": "sep", "texto": "…"})
        elif linha[0] == "+":
            saida.append({"tipo": "add", "texto": linha[1:]})
        elif linha[0] == "-":
            saida.append({"tipo": "del", "texto": linha[1:]})
        else:
            saida.append({"tipo": "ctx", "texto": linha[1:]})
    return saida


def montar_e2(it, v1, v2, tipos_resumo):
    vt = it["por_tipo"]["valor_total"]
    resp_v1, resp_v2 = vt["respostas"], vt["respostas_v2"]
    outros = {t: d for t, d in it["por_tipo"].items() if t != "valor_total"}
    sem_regressao = not it["piorou"] and all(d["certas_v2"] >= d["certas_v1"] for d in outros.values())
    resultado = (f"Duas linhas acrescentadas ao prompt levaram o acerto de {pct(it['acerto_v1'])} para {pct(it['acerto_v2'])}"
                 f"{', sem regressão' if sem_regressao else ''} e com custo por resposta menor." if it["custo_v2"] < it["custo_v1"] else
                 f"Duas linhas acrescentadas ao prompt levaram o acerto de {pct(it['acerto_v1'])} para {pct(it['acerto_v2'])}.")
    diff = diff_prompts(v1, v2)
    return {"id": "E2", **cb.EXPERIMENTOS["E2"], "o_que_testei": f"O T4 v1 contra o T4 v2 (duas linhas a mais no system prompt), nos mesmos {it['casos']} pedidos, 3 repetições cada.",
            "medido": True, "status": "medido", "resultado": resultado,
            "numero": f"{pct(it['acerto_v1'])} → {pct(it['acerto_v2'])}; tipo \"valor total\": {vt['certas_v1']}/{resp_v1} → {vt['certas_v2']}/{resp_v2}",
            "grupos": [{"titulo": "Acerto por caso (50 casos × 3 repetições)", "barras": [
                {"rotulo": f"T4 v1 ({v1['hash12']})", "valor": it["acerto_v1"], "texto": pct(it["acerto_v1"]), "sub": f"{usd(it['custo_v1'])} por resposta"},
                {"rotulo": f"T4 v2 ({v2['hash12']})", "valor": it["acerto_v2"], "texto": pct(it["acerto_v2"]), "sub": f"{usd(it['custo_v2'])} por resposta"}]}],
            "quando_usar": "Quando um tipo de erro se repete, leia os erros, escreva a regra que falta no prompt e rode de novo no mesmo conjunto para conferir que nada piorou. Depois valide em casos que a regra nunca viu (ainda não feito).",
            "placar": {"antes": vt["certas_v1"], "depois": vt["certas_v2"], "de": resp_v2, "tipo": "valor total"},
            "melhoraram": it["melhorou"], "pioraram": it["piorou"], "p_sinal": it["p_sinal"], "sem_regressao": sem_regressao,
            "tokens_saida": [it["tokens_saida_v1"], it["tokens_saida_v2"]], "diff": diff, "hash_v1": v1["hash12"], "hash_v2": v2["hash12"]}


# ------------------------------------------------------------------ E3, E4, E5
def interpretar(exp, comp, base, alt):
    """-> (resultado, quando_usar) com base só nos números medidos. Nunca declara vitória sem o teste pareado."""
    n, dif, p = comp["casos_comparados"], comp["diferenca_acerto_pp"], comp["p_sinal"]
    ra, rb = ab.ROTULOS[comp["base"]], ab.ROTULOS[comp["alternativa"]]
    pa, pb_ = base["acerto_caso_media"], alt["acerto_caso_media"]
    custo = comp["razao_custo"]
    custo_txt = (f"A variante \"{rb}\" custou {br(custo)} vez{'es' if custo >= 1.05 else ''} o custo por resposta ({usd(alt['custo_por_resposta_usd'])} contra {usd(base['custo_por_resposta_usd'])})."
                 if custo else "")
    sig = (f"A diferença passa no teste pareado (p = {br(p, 3)})." if p < 0.05 else
           f"Com {n} casos isso é um indício, não uma prova (teste pareado: p = {br(p, 3)}).")
    if abs(dif) < 0.05:
        r = f"Sem diferença de acerto: {pct(pa)} nas duas variantes. {custo_txt}"
        q = {"E3": "Se as definições já bastam, o zero-shot custa menos: comece por ele e só acrescente exemplos se o erro aparecer nos casos de borda.",
             "E4": "Com o mesmo acerto, o prompt único é mais simples; encadeie quando precisar guardar ou auditar a etapa intermediária (o JSON extraído).",
             "E5": "Sem ganho de acerto, o raciocínio só encarece: use-o quando a decisão exigir conta ou precedência entre regras e o modelo errar sem ele."}[exp]
    elif dif > 0:
        r = (f"\"{rb}\" acertou {pct(pb_)} contra {pct(pa)} de \"{ra}\" ({br(dif)} pontos a mais): melhor em {comp['a_favor_alternativa']} casos e pior em {comp['a_favor_base']}. {custo_txt} {sig}")
        q = {"E3": "Use exemplos quando as definições não resolvem os empates: escolha exemplos que ensinem a convenção dos casos ambíguos.",
             "E4": "Divida em dois prompts quando cada etapa tiver regra própria e você quiser conferir a saída da primeira; some o custo das duas chamadas.",
             "E5": "Vale pagar pelo raciocínio quando a decisão exige conta ou precedência entre regras; compare o ganho com o custo antes de adotar."}[exp]
    else:
        r = (f"\"{rb}\" acertou {pct(pb_)} contra {pct(pa)} de \"{ra}\" ({br(-dif)} pontos a menos): pior em {comp['a_favor_base']} casos e melhor em {comp['a_favor_alternativa']}. {custo_txt} {sig}")
        q = {"E3": "Os exemplos não ajudaram nestes casos: confira se eles ensinam a convenção certa antes de pagar por eles.",
             "E4": "O prompt único acertou mais neste conjunto: prefira-o, a menos que precise auditar a etapa intermediária.",
             "E5": "O raciocínio piorou o acerto neste conjunto: leia as respostas gravadas no Playground para ver onde errou."}[exp]
    return r.strip(), q


def montar_experimento_novo(exp, resumo_ab):
    base_v, alt_v = ab.PARES[exp]
    base, alt = resumo_ab["variantes"][f"{exp}/{base_v}"], resumo_ab["variantes"][f"{exp}/{alt_v}"]
    comp = resumo_ab["comparacoes"][exp]
    comum = {"id": exp, **cb.EXPERIMENTOS[exp]}
    if not (base["medido"] and alt["medido"]):
        return {**comum, "medido": False, "status": "nao_medido", "resultado": None, "numero": None, "grupos": [], "quando_usar": None,
                "pendencia": "Rodada ainda não executada: precisa da chave da API do autor. Nenhum resultado foi estimado.",
                "comando": f"{cb.COMANDOS['completo']} --so {exp}"}
    completo = base["completo"] and alt["completo"]
    resultado, quando = interpretar(exp, comp, base, alt)
    barras = [{"rotulo": ab.ROTULOS[v], "valor": s["acerto_caso_media"], "texto": pct(s["acerto_caso_media"]), "sub": f"{usd(s['custo_por_resposta_usd'])} por resposta"} for v, s in ((base_v, base), (alt_v, alt))]
    custo_max = max(s["custo_por_resposta_usd"] for s in (base, alt))
    barras_c = [{"rotulo": ab.ROTULOS[v], "valor": s["custo_por_resposta_usd"] / custo_max, "texto": usd(s["custo_por_resposta_usd"]), "sub": f"latência média {br(s['latencia_media_s'], 2)} s"} for v, s in ((base_v, base), (alt_v, alt))]
    n = base["casos"]
    return {**comum, "medido": True, "status": "medido" if completo else "parcial", "resultado": resultado,
            "numero": f"{pct(base['acerto_caso_media'])} contra {pct(alt['acerto_caso_media'])} ({ab.ROTULOS[base_v]} contra {ab.ROTULOS[alt_v]}), {n} casos × {base['repeticoes']} repetições",
            "grupos": [{"titulo": f"Acerto ({n} casos × {base['repeticoes']} repetições)", "barras": barras}, {"titulo": "Custo por resposta (a barra maior é o mais caro)", "barras": barras_c}],
            "quando_usar": quando, "comparacao": comp, "variantes": {base_v: base, alt_v: alt}}


# ------------------------------------------------------------------ prompts (biblioteca)
def _prompt_arquivo(d):
    return pb.carregar(d["id"], d["tecnica"], d["versao"])


def _segmentos(arq):
    seg = {"system": [], "user": []}
    por_local = {"system": [], "user": []}
    for a in arq["anatomia"]:
        por_local["system" if a["trecho"] in arq["system"] else "user"].append(a)
    seg["system"] = pb.segmentar(arq["system"], por_local["system"]) if arq["system"] else []
    seg["user"] = pb.segmentar(arq["user_template"], por_local["user"])
    return seg


def _exemplo(pid, casos, gab, variante_resumo, brutos):
    """Escolhe o caso do exemplo por regra fixa e junta a resposta real gravada, se existir."""
    if pid == "P3":
        caso = next(c for c in casos if len(gab[c["id"]]["faltantes"]) == 2)
        esperado = "Campos que faltam: " + ", ".join(dict(pb.P3_CAMPOS)[k] for k in gab[caso["id"]]["faltantes"])
    elif pid == "P5":
        caso = next(c for c in casos if c.get("subtipo") == "escalar_usd_converte")
        esperado = json.dumps(gab[caso["id"]], ensure_ascii=False)
    else:
        caso = next(c for c in casos if c["tipo"] == "borda")
        esperado = json.dumps(gab[caso["id"]], ensure_ascii=False)
    gravada = None
    if brutos:
        r = next((r for r in brutos if r["caso"] == caso["id"] and r["repeticao"] == 1), None)
        if r:
            gravada = {"resposta": r["resposta"], "correto": r["avaliacao"]["caso_correto"]}
    return {"caso": caso["id"], "entrada": caso["texto"], "esperado": esperado, "gravada": gravada}


def montar_prompts(resumo_ab, e1, e2, brutos_por_variante, raiz=RAIZ):
    saida = []
    for d in pb.definicoes():
        if d["papel"] != "biblioteca":
            continue
        arq = _prompt_arquivo(d)
        info = cb.PROMPTS[d["id"]]
        controles = [{"arquivo": f"prompts/{pb.nome_arquivo(c)}", "tecnica": c["tecnica"], "hash12": pb.hash_de(c)} for c in pb.definicoes() if c["id"] == d["id"] and c["papel"] == "controle"]
        item = {"id": d["id"], "nome": d["nome"], "tecnica": d["descricao_tecnica"], "versao": d["versao"], "hash12": arq["hash12"],
                "arquivo": f"prompts/{pb.nome_arquivo(d)}", "controles": controles, "problema": info["problema"], "quem_usa": info["quem_usa"],
                "tecnica_porque": info["tecnica_porque"], "system": arq["system"], "user_template": arq["user_template"],
                "anatomia": arq["anatomia"], "segmentos": _segmentos(arq),
                "partes": [{"parte": k, "rotulo": v} for k, v in pb.PARTES.items() if any(a["parte"] == k for a in arq["anatomia"])]}
        if d["id"] == "P1":
            t4v1, t4v2 = pl.carregar("T4", "v1"), pl.carregar("T4", "v2")
            it = _json(EXT_V2 / "iteracao.json")
            item.update({"medido": True, "acerto": {"valor": it["acerto_v2"], "texto": pct(it["acerto_v2"]), "base": "50 casos × 3 repetições, medido na iteração do T4",
                                                    "sufixo": " · casos de desenvolvimento", "nota": "Resultado de desenvolvimento: a regra foi escrita olhando os mesmos casos."},
                         "custo_chamada_usd": it["custo_v2"], "latencia_media_s": None, "extras": [],
                         "aprendi": e2["resultado"] + " " + f"Antes das duas linhas, o T4 v1 acertou {e2['placar']['antes']} de {e2['placar']['de']} respostas do tipo \"valor total\" (Experimento 2).",
                         "exemplo": {"caso": "D34", "entrada": next(c["texto"] for c in _json(EXT_V2 / "respostas_gravadas.json")["casos"] if c["id"] == "D34"),
                                     "esperado": json.dumps(next(c["gabarito"] for c in _json(EXT_V2 / "respostas_gravadas.json")["casos"] if c["id"] == "D34"), ensure_ascii=False),
                                     "gravada": {"rotulo": "Resposta gravada do T4 v1 (antes das duas linhas novas)", "resposta": next(c["saidas"]["T4"][0]["resposta"] for c in _json(EXT_V2 / "respostas_gravadas.json")["casos"] if c["id"] == "D34"), "correto": False},
                                     "nota": "As respostas brutas do T4 v2 não foram preservadas; só os totais da iteração (Experimento 2)."}})
            saida.append(item)
            continue
        chave = {"P2": "E3/few_shot", "P3": "E4/encadeado", "P4": "P4/saida_estruturada", "P5": "E5/cot"}[d["id"]]
        v = resumo_ab["variantes"][chave]
        dados = {"P2": "p2", "P3": "p3", "P4": "p4", "P5": "p5"}[d["id"]]
        casos, gab = ex.carregar_dados(dados, raiz / "dados" / "biblioteca")
        exemplo = _exemplo(d["id"], casos, gab, v, brutos_por_variante.get(tuple(chave.split("/"))))
        exemplo["nota"] = None if exemplo["gravada"] else "A resposta real do modelo ainda não foi gravada (rodada pendente). Abaixo, só a entrada e o gabarito."
        extras = []
        if v["medido"]:
            if d["id"] == "P3":
                extras = [f"E-mails no formato pedido: {pct(v['extras']['formato_ok'])}", f"Campos que faltou citar: {v['extras']['faltou_citar_total']}", f"Campos citados a mais: {v['extras']['citou_a_mais_total']}"]
            if d["id"] == "P4":
                extras = [f"Respostas com invenção de número ou valor: {v['extras']['respostas_com_invencao']} de {v['respostas']}"]
            item.update({"medido": True, "acerto": {"valor": v["acerto_caso_media"], "texto": pct(v["acerto_caso_media"]), "base": f"{v['casos']} casos × {v['repeticoes']} repetições", "nota": None if v["completo"] else "Rodada incompleta."},
                         "custo_chamada_usd": v["custo_por_resposta_usd"], "latencia_media_s": v["latencia_media_s"], "extras": extras,
                         "chamadas_por_resposta": v["chamadas_por_resposta"], "aprendi": info["aprendi_projeto"]})
        else:
            item.update({"medido": False, "acerto": None, "custo_chamada_usd": None, "latencia_media_s": None, "extras": [],
                         "aprendi": info["aprendi_projeto"], "pendencia": "Acerto e custo ainda não medidos (a rodada depende da chave da API do autor)."})
        item["exemplo"] = exemplo
        saida.append(item)
    return saida


# ------------------------------------------------------------------ playground
def montar_playground(resumo_ab, brutos_por_variante, raiz=RAIZ):
    grupos = []
    rg = _json(EXT_V2 / "respostas_gravadas.json")
    vistos, escolhidos = set(), []
    for c in rg["casos"]:
        if c["tipo"] == "valor_total" or c["tipo"] not in vistos:
            escolhidos.append(c)
            vistos.add(c["tipo"])
    casos = []
    for c in escolhidos:
        casos.append({"id": c["id"], "tipo": c["tipo"], "texto": c["texto"], "gabarito": c["gabarito"],
                      "variantes": [{"id": t, "rotulo": NOMES_TEC[t], "reps": [{"resposta": s["resposta"], "correto": s["correto"], "campos": s["campos"]} for s in c["saidas"][t]]} for t in NOMES_TEC]})
    grupos.append({"id": "E1", "rotulo": "Experimento 1: extração, 4 técnicas", "medido": True, "casos": casos,
                   "nota": "Respostas reais gravadas do claude-haiku-5-5 com os prompts v1 (T1 a T4). Mostro todos os 4 casos de \"valor total\" e 1 caso de cada outro tipo."})
    rotulos = {"E3": "Experimento 3: classificação", "E4": "Experimento 4: encadear ou único", "E5": "Experimento 5: decisão", "P4": "Prompt P4: resumo de reclamação"}
    dados_de = {"E3": "p2", "E4": "p3", "E5": "p5", "P4": "p4"}
    for exp in ("E3", "E4", "E5", "P4"):
        variantes = [v for e, v in ex.ORDEM if e == exp]
        if not all(brutos_por_variante.get((exp, v)) for v in variantes):
            grupos.append({"id": exp, "rotulo": rotulos[exp], "medido": False, "casos": [], "nota": "Rodada ainda não executada: não há respostas gravadas."})
            continue
        casos_d, gab = ex.carregar_dados(dados_de[exp], raiz / "dados" / "biblioteca")
        itens = []
        for c in casos_d:
            vs = []
            for v in variantes:
                regs = sorted((r for r in brutos_por_variante[(exp, v)] if r["caso"] == c["id"]), key=lambda r: r["repeticao"])
                vs.append({"id": v, "rotulo": ab.ROTULOS[v], "reps": [{"resposta": r["resposta"], "correto": r["avaliacao"]["caso_correto"], "campos": r["avaliacao"]["campos"]} for r in regs]})
            itens.append({"id": c["id"], "tipo": c["tipo"], "texto": c["texto"], "gabarito": gab[c["id"]], "variantes": vs})
        grupos.append({"id": exp, "rotulo": rotulos[exp], "medido": True, "casos": itens, "nota": "Respostas reais gravadas do claude-haiku-5-5. Não são chamadas ao vivo."})
    return grupos


# ------------------------------------------------------------------ resumo único
def construir(raiz=RAIZ, pasta_brutos=ex.BRUTOS, pasta_piloto=ex.PILOTO):
    resumo_v2 = _json(EXT_V2 / "resumo.json")
    casos_v2 = _json(raiz / "dados" / "extracao" / "v2" / "casos_teste.json")
    it = _json(EXT_V2 / "iteracao.json")
    resumo_ab = ab.resumir_tudo(pasta_brutos, pasta_piloto)
    brutos = ab.carregar_brutos(pasta_brutos)
    e1 = montar_e1(resumo_v2, casos_v2)
    e2 = montar_e2(it, pl.carregar("T4", "v1"), pl.carregar("T4", "v2"), None)
    experimentos = [e1, e2] + [montar_experimento_novo(x, resumo_ab) for x in ("E3", "E4", "E5")]
    prompts = montar_prompts(resumo_ab, e1, e2, brutos, raiz)
    novo = resumo_ab["custo_novo_usd"]["total"]
    anterior = sum(x["usd"] for x in GASTO_DETALHE)
    assert abs(anterior - ex.GASTO_ANTERIOR_USD) < 1e-9, "o gasto anterior do livro-caixa difere da constante do controle de custo"
    medidos = [e for e in experimentos if e["status"] == "medido"]
    r = {
        "projeto": {"nome": cb.NOME, "frase_impacto": cb.FRASE_IMPACTO, "empresa_nota": cb.EMPRESA_NOTA, "repo": cb.REPO, "demo": cb.DEMO,
                    "modelo": "claude-haiku-5-5", "esforco": "low", "prompts": len(prompts), "experimentos": len(experimentos),
                    "experimentos_medidos": len(medidos), "prompts_medidos": sum(1 for p in prompts if p["medido"]),
                    "limitacoes": cb.LIMITACOES},
        "custo": {"anterior_usd": anterior, "novo_usd": novo, "total_usd": anterior + novo, "teto_total_usd": ex.TETO_TOTAL_USD,
                  "teto_rodadas_novas_usd": ex.TETO_RODADAS_USD, "sobra_usd": ex.TETO_TOTAL_USD - anterior - novo,
                  "sobra_rodadas_novas_usd": ex.TETO_RODADAS_USD - novo, "detalhe_anterior": GASTO_DETALHE,
                  "novo_piloto_usd": resumo_ab["custo_novo_usd"]["piloto"], "novo_rodadas_usd": resumo_ab["custo_novo_usd"]["rodadas"],
                  "chamadas_novas": resumo_ab["chamadas_novas"]},
        "prompts": prompts, "experimentos": experimentos, "partes_legenda": [{"parte": k, "rotulo": v} for k, v in pb.PARTES.items()],
        "playground": montar_playground(resumo_ab, brutos, raiz),
        "como_medi": {"casos_extracao": e1["casos_total"], "casos_novos": 20, "repeticoes": ex.REPETICOES, "comandos": cb.COMANDOS},
        "pendencias": [e["id"] for e in experimentos if e["status"] != "medido"],
    }
    return r


def main():
    r = construir()
    SAIDA.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    p = r["projeto"]
    print(f"resumo.json: {p['prompts']} prompts ({p['prompts_medidos']} com medição), {p['experimentos']} experimentos ({p['experimentos_medidos']} medidos), "
          f"custo total US$ {r['custo']['total_usd']:.6f}; pendentes: {', '.join(r['pendencias']) or 'nenhum'}")


if __name__ == "__main__":
    main()
