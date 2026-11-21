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
import math
from pathlib import Path

import analisar_biblioteca as ab
import conteudo_biblioteca as cb
import diagnostico as dgn
import textos_diagnostico as td
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
        certas_vt = round(math.fsum(r["acerto_por_caso"][c] for c in casos_vt) * reps)
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
    return {"id": "E2", **cb.EXPERIMENTOS["E2"], "o_que_testei": f"O T4 (o prompt com system prompt) em duas versões, v1 contra v2 (duas linhas a mais), nos mesmos {it['casos']} pedidos, 3 repetições cada.",
            "medido": True, "status": "medido", "resultado": resultado,
            "numero": f"{pct(it['acerto_v1'])} → {pct(it['acerto_v2'])}; tipo \"valor total\": {vt['certas_v1']}/{resp_v1} → {vt['certas_v2']}/{resp_v2}",
            "grupos": [{"titulo": "Acerto por caso (50 casos × 3 repetições)", "barras": [
                {"rotulo": f"T4 v1 ({v1['hash12']})", "valor": it["acerto_v1"], "texto": pct(it["acerto_v1"]), "sub": f"{usd(it['custo_v1'])} por resposta"},
                {"rotulo": f"T4 v2 ({v2['hash12']})", "valor": it["acerto_v2"], "texto": pct(it["acerto_v2"]), "sub": f"{usd(it['custo_v2'])} por resposta"}]}],
            "quando_usar": "Quando um tipo de erro se repete, leia os erros, escreva a regra que falta no prompt e rode de novo no mesmo conjunto para conferir que nada piorou. Depois valide em casos que a regra nunca viu (feito aqui em 20 pedidos novos).",
            "placar": {"antes": vt["certas_v1"], "depois": vt["certas_v2"], "de": resp_v2, "tipo": "valor total"},
            "melhoraram": it["melhorou"], "pioraram": it["piorou"], "p_sinal": it["p_sinal"], "sem_regressao": sem_regressao,
            "tokens_saida": [it["tokens_saida_v1"], it["tokens_saida_v2"]], "diff": diff, "hash_v1": v1["hash12"], "hash_v2": v2["hash12"]}


# ------------------------------------------------------------------ E3, E4, E5
def cs(n):
    return f"{n} caso" + ("" if n == 1 else "s")


def interpretar(exp, comp, base, alt):
    """-> (resultado, quando_usar) com base só nos números medidos. Nunca declara vitória sem o teste pareado."""
    n, dif, p = comp["casos_comparados"], comp["diferenca_acerto_pp"], comp["p_sinal"]
    ra, rb = ab.ROTULOS[comp["base"]], ab.ROTULOS[comp["alternativa"]]
    pa, pb_ = base["acerto_caso_media"], alt["acerto_caso_media"]
    custo = comp["razao_custo"]
    custo_txt = (f"A variante \"{rb}\" custou {br(custo)} vez{'es' if custo >= 1.05 else ''} o custo por resposta ({usd(alt['custo_por_resposta_usd'])} contra {usd(base['custo_por_resposta_usd'])})."
                 if custo else "")
    sig = ("A diferença é grande o bastante para não ser acaso (detalhes no apêndice)." if p < 0.05 else
           f"Com {n} casos isso é um indício, não uma prova.")
    if abs(dif) < 0.05:
        r = f"Sem diferença de acerto: {pct(pa)} nas duas variantes. {custo_txt}"
        q = {"E3": "Se as definições já bastam, o zero-shot custa menos: comece por ele e só acrescente exemplos se o erro aparecer nos casos de borda.",
             "E4": "Com o mesmo acerto, o prompt único é mais simples; encadeie quando precisar guardar ou auditar a etapa intermediária (o JSON extraído).",
             "E5": "Sem ganho de acerto, o raciocínio só encarece: use-o quando a decisão exigir conta ou precedência entre regras e o modelo errar sem ele."}[exp]
    elif dif > 0:
        r = (f"\"{rb}\" acertou {pct(pb_)} contra {pct(pa)} de \"{ra}\" ({br(dif)} pontos a mais): melhor em {cs(comp['a_favor_alternativa'])} e pior em {comp['a_favor_base']}. {custo_txt} {sig}")
        q = {"E3": "Use exemplos quando as definições não resolvem os empates: escolha exemplos que ensinem a convenção dos casos ambíguos.",
             "E4": "Divida em dois prompts quando cada etapa tiver regra própria e você quiser conferir a saída da primeira; some o custo das duas chamadas.",
             "E5": "Vale pagar pelo raciocínio quando a decisão exige conta ou precedência entre regras; compare o ganho com o custo antes de adotar."}[exp]
    else:
        r = (f"\"{rb}\" acertou {pct(pb_)} contra {pct(pa)} de \"{ra}\" ({br(-dif)} pontos a menos): pior em {cs(comp['a_favor_base'])} e melhor em {comp['a_favor_alternativa']}. {custo_txt} {sig}")
        q = {"E3": "Os exemplos não ajudaram nestes casos: confira se eles ensinam a convenção certa antes de pagar por eles.",
             "E4": "O prompt único acertou um pouco mais, mas a diferença é pequena e não é conclusiva, e os dois custaram parecido. Encadeie se precisar guardar e conferir o JSON da etapa intermediária; senão, comece pelo prompt único.",
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


def montar_e6(resumo_ab, dg):
    comp = resumo_ab["comparacoes"]["E6"]
    base, alt = resumo_ab["variantes"]["E4/encadeado"], resumo_ab["variantes"]["E6/encadeado_v2"]
    comum = {"id": "E6", **cb.EXPERIMENTOS["E6"]}
    if not (base["medido"] and alt["medido"]):
        return {**comum, "medido": False, "status": "nao_medido", "resultado": None, "numero": None, "grupos": [], "quando_usar": None,
                "pendencia": "Rodada ainda não executada: precisa da chave da API do autor. Nenhum resultado foi estimado.", "comando": f"{cb.COMANDOS['completo']} --so E6"}
    completo = base["completo"] and alt["completo"]
    dif = comp["diferenca_acerto_pp"]
    resultado = (f"O P3 v2 acertou {pct(alt['acerto_caso_media'])} contra {pct(base['acerto_caso_media'])} do P3 v1 ({br(dif)} pontos a mais): melhor em {cs(comp['a_favor_alternativa'])} e pior em {comp['a_favor_base']}, "
                 f"com custo de {br(comp['razao_custo'], 2)}× por resposta. Campos citados a mais: {base['extras']['citou_a_mais_total']} no v1 e {alt['extras']['citou_a_mais_total']} no v2.")
    barras = [{"rotulo": ab.ROTULOS[v], "valor": s_["acerto_caso_media"], "texto": pct(s_["acerto_caso_media"]), "sub": f"{usd(s_['custo_por_resposta_usd'])} por resposta"} for v, s_ in (("encadeado_v1", base), ("encadeado_v2", alt))]
    custo_max = max(base["custo_por_resposta_usd"], alt["custo_por_resposta_usd"])
    barras_c = [{"rotulo": ab.ROTULOS[v], "valor": s_["custo_por_resposta_usd"] / custo_max, "texto": usd(s_["custo_por_resposta_usd"]), "sub": f"latência média {br(s_['latencia_media_s'], 2)} s"} for v, s_ in (("encadeado_v1", base), ("encadeado_v2", alt))]
    n = base["casos"]
    v1p, v2p = pb.carregar("P3", "encadeado", "v1"), pb.carregar("P3", "encadeado", "v2")
    return {**comum, "medido": True, "status": "medido" if completo else "parcial", "resultado": resultado,
            "diff": diff_prompts(v1p, v2p), "hash_v1": v1p["hash12"], "hash_v2": v2p["hash12"], "arquivo_v2": "prompts/P3_encadeado_v2.json",
            "numero": f"{pct(base['acerto_caso_media'])} contra {pct(alt['acerto_caso_media'])} (P3 v1 contra P3 v2), {n} casos × {base['repeticoes']} repetições",
            "grupos": [{"titulo": f"Acerto ({n} casos × {base['repeticoes']} repetições)", "barras": barras}, {"titulo": "Custo por resposta (a barra maior é o mais caro)", "barras": barras_c}],
            "quando_usar": td.quando_usar_e6(dg) if dg else None, "explicacao": td.explicacao_e6(dg) if dg else None,
            "comparacao": comp, "variantes": {"encadeado_v1": base, "encadeado_v2": alt}}


def montar_validacao():
    """Validação do T4 v2 em 20 pedidos novos (resultados/extracao/v3/validacao.json), se já medida."""
    arq = RAIZ / "resultados" / "extracao" / "v3" / "validacao.json"
    if not arq.exists():
        return None
    v = _json(arq)
    if not v.get("completo"):
        return None
    vt = v["veredito"]
    t = v["por_tipo"]["valor_total"]
    return {"casos": v["casos"], "acerto_v1": v["acerto_v1"], "acerto_v2": v["acerto_v2"], "custo_v1": v["custo_v1"], "custo_v2": v["custo_v2"],
            "tokens_saida_v1": v["tokens_saida_v1"], "tokens_saida_v2": v["tokens_saida_v2"], "veredito": vt, "casos_valor_total": t["casos"],
            "texto": (f"Testei as duas versões em {v['casos']} pedidos novos, escritos por script com outra seed e congelados antes de rodar. No tipo \"valor total\", a v1 acertou {vt['valor_total_certas_v1']}/{vt['valor_total_respostas']} e a v2 "
                      f"{vt['valor_total_certas_v2']}/{vt['valor_total_respostas']}. Nos outros tipos, {vt['resto_certas_v1']}/{vt['resto_respostas']} contra {vt['resto_certas_v2']}/{vt['resto_respostas']}: "
                      f"sem regressão. Acerto geral {pct(v['acerto_v1'])} contra {pct(v['acerto_v2'])}; a v2 também custou menos por resposta ({usd(v['custo_v2'])} contra {usd(v['custo_v1'])}) e gastou menos tokens de saída."),
            "criterio": f"Critério escrito antes da rodada: a regra \"generaliza\" se a v2 acertar pelo menos 17 das {vt['valor_total_respostas']} respostas de valor total e não ficar pior nos outros tipos. Resultado: {'generalizou' if vt['generaliza'] else 'não generalizou'}.",
            "ressalva": f"São só {t['casos']} casos de valor total, escritos pelo mesmo gerador de frases dos 50 casos anteriores, e o gabarito é meu. Mostra que a regra não foi decorada, não que vale para qualquer pedido real."}


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
    if brutos_por_variante.get(("E6", "encadeado_v2")) and brutos_por_variante.get(("E4", "encadeado")):
        casos_d, gab = ex.carregar_dados("p3", raiz / "dados" / "biblioteca")
        itens = []
        for c in casos_d:
            vs = []
            for chave, rot in ((("E4", "encadeado"), "P3 v1 (E-mail com proibição)"), (("E6", "encadeado_v2"), "P3 v2 (E-mail com instrução)")):
                regs = sorted((r for r in brutos_por_variante[chave] if r["caso"] == c["id"]), key=lambda r: r["repeticao"])
                vs.append({"id": chave[1], "rotulo": rot, "reps": [{"resposta": r["resposta"], "correto": r["avaliacao"]["caso_correto"], "campos": r["avaliacao"]["campos"]} for r in regs]})
            itens.append({"id": c["id"], "tipo": c["tipo"], "texto": c["texto"], "gabarito": gab[c["id"]], "variantes": vs})
        grupos.append({"id": "E6", "rotulo": "Experimento 6: e-mail P3 v1 contra v2", "medido": True, "casos": itens, "nota": "Respostas reais gravadas do claude-haiku-5-5, mesmos 20 casos do Experimento 4. Não são chamadas ao vivo."})
    return grupos


# ------------------------------------------------------------------ destaques e conclusão
def montar_destaques(e1, e2, novos, e6=None):
    d = [{"ancora": "exp-e1", "grande": f"{e1['casos_sem_diferenca']} de {e1['casos_total']}", "rotulo": "pedidos em que as 4 técnicas acertaram igual (E1)"},
         {"ancora": "exp-e2", "grande": f"{e2['placar']['antes']}/{e2['placar']['de']} → {e2['placar']['depois']}/{e2['placar']['de']}",
          "rotulo": f"respostas certas no tipo \"{e2['placar']['tipo']}\" depois de 2 linhas novas no prompt (E2)"}]
    for e in novos:
        if e["status"] != "medido":
            continue
        base_v, alt_v = ab.PARES[e["id"]]
        b, a = e["variantes"][base_v], e["variantes"][alt_v]
        d.append({"ancora": "exp-" + e["id"].lower(), "grande": f"{pct(a['acerto_caso_media'])} vs {pct(b['acerto_caso_media'])}",
                  "rotulo": f"{ab.ROTULOS[alt_v]} contra {ab.ROTULOS[base_v]}, a {br(e['comparacao']['razao_custo'])}× o custo ({e['id']})"})
    if e6 and e6["status"] == "medido":
        b, a = e6["variantes"]["encadeado_v1"], e6["variantes"]["encadeado_v2"]
        d.append({"ancora": "exp-e6", "grande": f"{pct(b['acerto_caso_media'])} → {pct(a['acerto_caso_media'])}", "rotulo": "e-mail com o prompt reescrito depois de ler os erros (E6, casos de desenvolvimento)"})
    return d


def montar_conclusao(e1, e2, novos, prompts, resumo_ab, dg=None, e6=None):
    pode, nao_pode = [], []
    pl_ = e2["placar"]
    pode.append({"titulo": "Uma regra de negócio escrita no prompt corrige um erro que se repete.",
                 "texto": f"Duas linhas novas levaram o tipo \"{pl_['tipo']}\" de {pl_['antes']}/{pl_['de']} para {pl_['depois']}/{pl_['de']} respostas certas, sem nenhum caso pior (E2). "
                          + (f"Em {e2['validacao']['casos']} pedidos novos, o tipo \"valor total\" foi de {e2['validacao']['veredito']['valor_total_certas_v1']}/{e2['validacao']['veredito']['valor_total_respostas']} para {e2['validacao']['veredito']['valor_total_certas_v2']}/{e2['validacao']['veredito']['valor_total_respostas']}, sem regressão nos outros tipos, mas com só {e2['validacao']['casos_valor_total']} casos desse tipo."
                            if e2.get("validacao") else "Vale para os casos em que a regra foi escrita; falta testar em pedidos novos.")})
    razao = e1["tecnicas"]["T3"]["custo_resposta_usd"] / e1["tecnicas"]["T1"]["custo_resposta_usd"]
    pode.append({"titulo": "Em extração simples, escrever a regra pesou mais do que escolher a técnica.",
                 "texto": f"Em {e1['casos_sem_diferenca']} de {e1['casos_total']} pedidos as quatro técnicas acertaram igual (E1). O raciocínio passo a passo custou {br(razao)} vezes o zero-shot por resposta."})
    medidos = {e["id"]: e for e in novos if e["status"] == "medido"}
    def delta(e):
        c = e["comparacao"]
        base_v, alt_v = ab.PARES[e["id"]]
        return (e["variantes"][alt_v]["acerto_caso_media"], e["variantes"][base_v]["acerto_caso_media"], c["razao_custo"], c["a_favor_base"] + c["a_favor_alternativa"])
    if "E3" in medidos and "E5" in medidos:
        a3, b3, r3, n3 = delta(medidos["E3"])
        a5, b5, r5, n5 = delta(medidos["E5"])
        pode.append({"titulo": "Exemplos e raciocínio apontam para mais acerto, e custam mais.",
                     "texto": f"Few-shot acertou {pct(a3)} contra {pct(b3)} (E3, {br(r3)}× o custo) e o raciocínio {pct(a5)} contra {pct(b5)} (E5, {br(r5)}× o custo). "
                              f"A direção é favorável nos dois, mas a diferença apareceu em {cs(n3)} no E3 e em {cs(n5)} no E5."})
    if "E4" in medidos:
        e = medidos["E4"]
        a4, b4, r4, n4 = delta(e)
        vs = e["variantes"]
        falt = sum(v["extras"]["faltou_citar_total"] for v in vs.values())
        mais = {k: v["extras"]["citou_a_mais_total"] for k, v in vs.items()}
        erro_txt = (f"Em nenhum dos dois fluxos o e-mail deixou de citar um campo que faltava; todos os erros foram citar campo a mais ({mais['encadeado']} no encadeado e {mais['unico']} no prompt único, em {vs['encadeado']['respostas']} respostas cada)."
                    if falt == 0 else f"Os erros incluíram {falt} campos que faltavam e não foram citados, além de campos citados a mais.")
        if dg:
            pode.append(td.conclusao_e4(dg, a4, b4))
        else:
            pode.append({"titulo": "Encadear dois prompts não foi melhor do que pedir tudo de uma vez.",
                         "texto": f"O fluxo encadeado acertou {pct(a4)} contra {pct(b4)} do prompt único, com custo parecido (E4). {erro_txt}"})
    if e6 and e6["status"] == "medido":
        b6, a6 = e6["variantes"]["encadeado_v1"], e6["variantes"]["encadeado_v2"]
        pode.append({"titulo": "Medir, ler os erros e reescrever o prompt funcionou no e-mail.",
                     "texto": f"O P3 v2 acertou {pct(a6['acerto_caso_media'])} contra {pct(b6['acerto_caso_media'])} do v1 (E6), a {br(e6['comparacao']['razao_custo'], 2)}× o custo. "
                              "A v2 foi escrita depois de ler os erros nos mesmos 20 casos, então é resultado de desenvolvimento: falta testá-la em casos novos."})
    custos = [p["custo_chamada_usd"] for p in prompts if p["medido"]]
    pode.append({"titulo": "Testar prompts com número custa pouco.",
                 "texto": f"O projeto inteiro gastou {usd(resumo_ab['gasto_total_usd'], 4)} de um teto de {usd(ex.TETO_TOTAL_USD, 2)}. O custo médio por resposta ficou entre {usd(min(custos))} e {usd(max(custos))}, conforme o prompt."})
    ps = [(i, e["comparacao"]["p_sinal"]) for i, e in medidos.items()]
    sem_prova = [i for i, p in ps if p >= 0.05]
    nao_pode += ["Que esses números valem para dados reais: os dados são fictícios e mais regulares do que e-mails e chamados reais.",
                 "Que valem para outros modelos: só testei o claude-haiku-5-5, com esforço de raciocínio baixo.",
                 (f"Que as diferenças de {', '.join(sem_prova)} sejam sólidas: com 20 casos, poucos casos mudam o resultado, e nenhuma delas foi grande o bastante para descartar o acaso (detalhes no apêndice)."
                  if sem_prova else "Que o resultado vale além dos 20 casos testados."),
                 ("Que a regra do T4 v2 vale para qualquer pedido: ela foi validada em 20 pedidos novos, mas do mesmo estilo de frases e com só 6 casos de valor total." if e2.get("validacao")
                  else "Que a regra do T4 v2 vale para pedidos novos: ela foi escrita olhando os mesmos 50 pedidos em que foi medida."),
                 "Que o P3 v2 vale para e-mails novos: ele foi reescrito olhando os erros dos mesmos 20 casos em que foi medido." if e6 else "",
                 "Que o gabarito é neutro: fui a única pessoa a escrevê-lo."]
    nao_pode = [x for x in nao_pode if x]
    na_pratica = ["Comece pelo prompt mais simples e escreva nele as regras de negócio que importam.",
                  "Se o erro está nos casos de borda, teste exemplos (few-shot) e compare o custo.",
                  "Use raciocínio passo a passo quando a decisão exige conta ou precedência entre regras, e confira se o custo extra compensa.",
                  "Escreva o gabarito antes de rodar: sem ele não dá para saber se mudar o prompt melhorou ou piorou."]
    return {"resumo": "Dá para concluir o método (prompt estruturado, gabarito escrito antes, custo medido) e a direção dos resultados. Não dá para concluir que uma técnica é melhor que outra em geral.",
            "pode": pode, "nao_pode": nao_pode, "na_pratica": na_pratica}


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
    e2["validacao"] = montar_validacao()
    prompts = montar_prompts(resumo_ab, e1, e2, brutos, raiz)
    novo = resumo_ab["custo_novo_usd"]["total"]
    anterior = math.fsum(x["usd"] for x in GASTO_DETALHE)
    assert abs(anterior - ex.GASTO_ANTERIOR_USD) < 1e-9, "o gasto anterior do livro-caixa difere da constante do controle de custo"
    medidos = [e for e in experimentos if e["status"] == "medido"]
    for p in prompts:
        p["acerto_def"] = cb.ACERTO_DEF[p["id"]]
    novos = [e for e in experimentos if e["id"] in ("E3", "E4", "E5")]
    dg = dgn.construir(pasta_brutos, raiz) if all(e["status"] == "medido" for e in novos) else None
    if dg:   # textos escritos depois de ler os erros (src/diagnostico.py), no lugar dos escritos antes da medição
        por_id = {p["id"]: p for p in prompts}
        for pid, fn in (("P2", td.aprendi_p2), ("P3", td.aprendi_p3), ("P4", td.aprendi_p4), ("P5", td.aprendi_p5)):
            por_id[pid]["aprendi_preparo"] = por_id[pid]["aprendi"]
            por_id[pid]["aprendi"] = fn(dg)
        for e in novos:
            if e["id"] == "E3":
                e["explicacao"] = td.explicacao_e3(dg)
            elif e["id"] == "E4":
                e["explicacao"] = td.explicacao_e4(dg)
                e["quando_usar"] = td.quando_usar_e4(dg)
            else:
                e["explicacao"] = td.explicacao_e5(dg)
    e6 = montar_e6(resumo_ab, dg)
    experimentos.append(e6)
    medidos = [e for e in experimentos if e["status"] == "medido"]
    r = {
        "destaques": montar_destaques(e1, e2, novos, e6),
        "conclusao": montar_conclusao(e1, e2, novos, prompts, {"gasto_total_usd": anterior + novo}, dg, e6) if all(e["status"] == "medido" for e in novos) else None,
        "glossario": [{"termo": t, "def": d} for t, d in cb.GLOSSARIO],
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
