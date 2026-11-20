"""Lê as respostas brutas das rodadas novas (resultados/biblioteca/brutos/*.jsonl) e gera
resultados/biblioteca/resumo_biblioteca.json e resultados/biblioteca/RELATORIO.md.

Como cada número é medido (mesmas regras da extração, ver docs/medicao.md):
- Acerto por caso: média, sobre as repetições, de (resposta correta pela regra de src/avaliadores.py); depois média
  sobre os casos. Também o mínimo e o máximo entre as repetições.
- Custo: tokens informados pela API x preço de config/precos.json, somando todas as etapas da resposta (no fluxo
  encadeado do E4 são duas chamadas). Custo por acerto = custo total / respostas corretas.
- Latência: time.perf_counter em volta da chamada bem-sucedida, somada nas etapas; média e mediana.
- IC 95%: bootstrap percentil (10.000 reamostragens dos 20 casos, seed 42). Só no apêndice.
- Comparação: teste do sinal exato pareado por caso (empates excluídos). Com 20 casos e poucos casos discordantes,
  p < 0,05 é raro: a diferença é descrita como indício, nunca como prova.
- Respostas cortadas (stop_reason diferente de end_turn) são contadas.

Se uma variante não tem respostas, ela aparece com "medido": false. Nada é estimado.

Uso: python src/analisar_biblioteca.py
"""
import json
import statistics
from collections import defaultdict
from pathlib import Path

import analisar as an_ext
import experimentos as ex

RAIZ = Path(__file__).resolve().parent.parent

# (experimento) -> (variante base, variante alternativa). A "alternativa" é a opção mais elaborada/cara.
PARES = {"E3": ("zero_shot", "few_shot"), "E4": ("unico", "encadeado"), "E5": ("direto", "cot")}
ROTULOS = {"zero_shot": "Zero-shot", "few_shot": "Few-shot", "unico": "Prompt único (extrai e escreve)",
           "encadeado": "Encadeado (P1 → P3)", "direto": "Sem raciocínio", "cot": "Com raciocínio (chain-of-thought)",
           "saida_estruturada": "Saída estruturada"}


def carregar_brutos(pasta=ex.BRUTOS):
    por = {}
    for exp, var in ex.ORDEM:
        arq = Path(pasta) / f"{exp}_{var}.jsonl"
        if arq.exists():
            regs = [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()]
            if regs:
                por[(exp, var)] = regs
    return por


def carregar_piloto(pasta=ex.PILOTO):
    arq = Path(pasta) / "piloto.jsonl"
    return [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()] if arq.exists() else []


def _media(x):
    return sum(x) / len(x) if x else None


def resumir_variante(regs, n_casos=20, reps_planejadas=ex.REPETICOES):
    por_caso, por_tipo, por_rep, campos = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for r in regs:
        ok = 1.0 if r["avaliacao"]["caso_correto"] else 0.0
        por_caso[r["caso"]].append(ok)
        por_tipo[r["tipo"]].append(ok)
        por_rep[r["repeticao"]].append(ok)
        for k, v in r["avaliacao"]["campos"].items():
            campos[k].append(1.0 if v else 0.0)
    acerto_caso = {c: sum(v) / len(v) for c, v in por_caso.items()}
    vals = [acerto_caso[c] for c in sorted(acerto_caso)]
    lo, hi = an_ext.bootstrap_ic(vals) if vals else (None, None)
    custo = sum(r["custo_usd"] for r in regs)
    certas = sum(1 for r in regs if r["avaliacao"]["caso_correto"])
    etapas = [e for r in regs for e in r["etapas"]]
    lat = [r["latencia_s"] for r in regs]
    s = {
        "medido": True, "casos": len(por_caso), "respostas": len(regs), "repeticoes": max(por_rep),
        "completo": len(por_caso) == n_casos and all(len(v) == reps_planejadas for v in por_caso.values()),
        "prompts": sorted({f"{e['prompt']} {e['tecnica']} {e['versao']} {e['hash12']}" for e in etapas}),
        "acerto_caso_media": _media(vals), "acerto_caso_rep_min": min(_media(v) for v in por_rep.values()),
        "acerto_caso_rep_max": max(_media(v) for v in por_rep.values()), "ic95_baixo": lo, "ic95_alto": hi,
        "acerto_por_caso": dict(sorted(acerto_caso.items())),
        "acerto_tipo": {t: _media(v) for t, v in sorted(por_tipo.items())},
        "acerto_campo": {k: _media(v) for k, v in campos.items()},
        "json_valido": _media([1.0 if r["avaliacao"]["json_valido"] else 0.0 for r in regs]),
        "truncadas": sum(1 for r in regs if any(e["stop_reason"] not in (None, "end_turn") for e in r["etapas"])),
        "chamadas_por_resposta": _media([len(r["etapas"]) for r in regs]),
        "tokens_entrada_media": _media([sum(e["tokens_entrada"] for e in r["etapas"]) for r in regs]),
        "tokens_saida_media": _media([sum(e["tokens_saida"] for e in r["etapas"]) for r in regs]),
        "custo_total_usd": custo, "custo_por_resposta_usd": custo / len(regs),
        "custo_por_acerto_usd": (custo / certas) if certas else None,
        "latencia_media_s": _media(lat), "latencia_mediana_s": statistics.median(lat),
    }
    ex_ = [r["avaliacao"] for r in regs]
    if "formato_ok" in ex_[0]:   # P3
        s["extras"] = {"formato_ok": _media([1.0 if a["formato_ok"] else 0.0 for a in ex_]),
                       "faltou_citar_total": sum(len(a["faltou_citar"]) for a in ex_),
                       "citou_a_mais_total": sum(len(a["citou_a_mais"]) for a in ex_),
                       "palavras_corpo_media": _media([a["palavras_corpo"] for a in ex_])}
        s["json_valido"] = None  # não se aplica a e-mail
    if "invencoes" in ex_[0]:    # P4
        s["extras"] = {"invencoes_total": sum(a["invencoes"] for a in ex_),
                       "respostas_com_invencao": sum(1 for a in ex_ if a["invencoes"])}
    return s


def comparar_par(a, b):
    """A = base, B = alternativa. -> dict com casos a favor de cada um e p do teste do sinal exato."""
    ca, cb = a["acerto_por_caso"], b["acerto_por_caso"]
    casos = sorted(set(ca) & set(cb))
    fa, fb, p = an_ext.teste_sinal_exato([ca[c] for c in casos], [cb[c] for c in casos])
    return {"casos_comparados": len(casos), "a_favor_base": fa, "a_favor_alternativa": fb, "p_sinal": p,
            "casos_melhores_na_alternativa": [c for c in casos if cb[c] > ca[c]],
            "casos_melhores_na_base": [c for c in casos if ca[c] > cb[c]],
            "diferenca_acerto_pp": (b["acerto_caso_media"] - a["acerto_caso_media"]) * 100,
            "razao_custo": (b["custo_por_resposta_usd"] / a["custo_por_resposta_usd"]) if a["custo_por_resposta_usd"] else None,
            "razao_latencia": (b["latencia_media_s"] / a["latencia_media_s"]) if a["latencia_media_s"] else None}


def resumir_tudo(pasta_brutos=ex.BRUTOS, pasta_piloto=ex.PILOTO):
    brutos = carregar_brutos(pasta_brutos)
    variantes = {}
    for exp, var in ex.ORDEM:
        regs = brutos.get((exp, var))
        variantes[f"{exp}/{var}"] = resumir_variante(regs) if regs else {"medido": False}
    comps = {}
    for exp, (base, alt) in PARES.items():
        a, b = variantes[f"{exp}/{base}"], variantes[f"{exp}/{alt}"]
        comps[exp] = {"base": base, "alternativa": alt, **(comparar_par(a, b) if a["medido"] and b["medido"] else {"medido": False})}
    piloto = carregar_piloto(pasta_piloto)
    custo_piloto = sum(r["custo_usd"] for r in piloto)
    custo_rodadas = sum(r["custo_usd"] for regs in brutos.values() for r in regs)
    return {"variantes": variantes, "comparacoes": comps,
            "custo_novo_usd": {"piloto": custo_piloto, "rodadas": custo_rodadas, "total": custo_piloto + custo_rodadas},
            "chamadas_novas": len(piloto) + sum(len(r["etapas"]) for regs in brutos.values() for r in regs),
            "piloto_chamadas": len(piloto)}


def pct(x):
    return "—" if x is None else f"{x * 100:.1f}%".replace(".", ",")


def num(x, casas):
    return "—" if x is None else f"{x:.{casas}f}".replace(".", ",")


def usd(x):
    return "—" if x is None else f"{x:.6f}".replace(".", ",")


def relatorio(resumo):
    L = ["# Relatório das rodadas novas (P2 a P5)", "",
         "Gerado por `src/analisar_biblioteca.py` a partir de `resultados/biblioteca/brutos/`. Nenhum número foi digitado à mão.", "",
         f"Gasto novo: US$ {usd(resumo['custo_novo_usd']['total'])} (piloto US$ {usd(resumo['custo_novo_usd']['piloto'])}; rodadas US$ {usd(resumo['custo_novo_usd']['rodadas'])}).", "",
         "| Experimento | Variante | Acerto (média) | Mín–máx entre repetições | Custo por resposta (US$) | Custo por acerto (US$) | Latência média (s) | Respostas |", "|---|---|---|---|---|---|---|---|"]
    for chave, v in resumo["variantes"].items():
        exp, var = chave.split("/")
        if not v["medido"]:
            L.append(f"| {exp} | {ROTULOS[var]} | não medido | — | — | — | — | 0 |")
            continue
        L.append(f"| {exp} | {ROTULOS[var]} | {pct(v['acerto_caso_media'])} | {pct(v['acerto_caso_rep_min'])}–{pct(v['acerto_caso_rep_max'])} | "
                 f"{usd(v['custo_por_resposta_usd'])} | {usd(v['custo_por_acerto_usd'])} | {num(v['latencia_media_s'], 2)} | {v['respostas']} |")
    L += ["", "## Comparações pareadas (teste do sinal exato, empates excluídos)", "",
          "| Experimento | Base | Alternativa | Casos a favor da base | Casos a favor da alternativa | p |", "|---|---|---|---|---|---|"]
    for exp, c in resumo["comparacoes"].items():
        if c.get("medido") is False:
            L.append(f"| {exp} | {ROTULOS[c['base']]} | {ROTULOS[c['alternativa']]} | — | — | não medido |")
        else:
            L.append(f"| {exp} | {ROTULOS[c['base']]} | {ROTULOS[c['alternativa']]} | {c['a_favor_base']} | {c['a_favor_alternativa']} | {num(c['p_sinal'], 3)} |")
    return "\n".join(L) + "\n"


def main():
    resumo = resumir_tudo()
    ex.RESULTADOS.mkdir(parents=True, exist_ok=True)
    (ex.RESULTADOS / "resumo_biblioteca.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (ex.RESULTADOS / "RELATORIO.md").write_text(relatorio(resumo), encoding="utf-8", newline="\n")
    medidas = [k for k, v in resumo["variantes"].items() if v["medido"]]
    print(f"{len(medidas)} de {len(resumo['variantes'])} variantes com respostas; gasto novo US$ {resumo['custo_novo_usd']['total']:.6f}")


if __name__ == "__main__":
    main()
