"""P10: lê resultados/brutos/*.json e gera resultados/resumo.json e resultados/RELATORIO.md.

Como cada número é medido:
- Acerto por caso: por técnica, média sobre as repetições de (caso correto = JSON válido +
  schema pydantic válido + 8 campos iguais ao gabarito). Também reportado o mínimo e o máximo
  entre as repetições (acerto de cada repetição sobre os 50 casos).
- Acerto por campo / por tipo de caso: média sobre todas as respostas da técnica.
- JSON válido: fração de respostas em que o texto (ou o bloco <json> no T3) é um objeto JSON.
- Custo: tokens de entrada e saída informados pela API x preço de config/precos.json.
  Custo por acerto = custo total da técnica / número de respostas corretas.
- Latência: time.perf_counter em volta da chamada bem-sucedida; média e mediana em segundos.
- IC 95%: bootstrap percentil, 10.000 reamostragens dos 50 casos com reposição (seed 42),
  sobre o acerto médio por caso. Se os intervalos de duas técnicas se sobrepõem, a diferença
  NÃO é declarada vitória.
- Comparação entre técnicas: uma diferença só é declarada quando os IC não se sobrepõem E o teste do sinal
  exato pareado por caso (bilateral, empates excluídos) dá p < 0,05. O bootstrap percentil dá IC de largura
  zero quando a técnica acerta 100% dos casos, então a sobreposição de IC sozinha não basta
  (correção registrada após a auditoria de 2026-11-20).
- Respostas cortadas (stop_reason diferente de end_turn) são contadas e informadas.

Uso: python src/analisar.py [pasta_brutos]
"""
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import caminhos

RAIZ = caminhos.RAIZ
NOMES = {"T1": "zero-shot", "T2": "few-shot", "T3": "chain-of-thought", "T4": "system prompt"}
CAMPOS = ["solicitante_area", "item", "quantidade", "unidade", "prazo_entrega", "valor_unitario", "moeda", "fornecedor"]


def carregar(pasta):
    return [json.loads(a.read_text(encoding="utf-8")) for a in sorted(Path(pasta).glob("*.json"))]


def bootstrap_ic(valores, n=10_000, seed=42):
    rng = random.Random(seed)
    k = len(valores)
    medias = sorted(math.fsum(rng.choices(valores, k=k)) / k for _ in range(n))
    return medias[int(0.025 * n)], medias[int(0.975 * n) - 1]


def mediana(x):
    return statistics.median(x) if x else None


def resumir(regs):
    por_tec = defaultdict(list)
    for r in regs:
        por_tec[r["tecnica"]].append(r)
    saida = {}
    for tid in sorted(por_tec):
        rs = por_tec[tid]
        por_caso = defaultdict(list)
        por_rep = defaultdict(list)
        por_tipo = defaultdict(list)
        for r in rs:
            ok = 1.0 if r["avaliacao"]["caso_correto"] else 0.0
            por_caso[r["caso"]].append(ok)
            por_rep[r["repeticao"]].append(ok)
            por_tipo[r["tipo"]].append(ok)
        media_caso = [math.fsum(v) / len(v) for v in por_caso.values()]
        acertos = sum(1 for r in rs if r["avaliacao"]["caso_correto"])
        custo = math.fsum(r["custo_usd"] for r in rs)
        lat = [r["latencia_s"] for r in rs]
        rep_acc = [math.fsum(v) / len(v) for v in por_rep.values()]
        ic = bootstrap_ic(media_caso)
        saida[tid] = {
            "tecnica": NOMES.get(tid, tid), "prompt_hash12": rs[0]["prompt_hash12"], "prompt_versao": rs[0]["prompt_versao"],
            "casos": len(por_caso), "respostas": len(rs), "repeticoes": len(por_rep),
            "acerto_caso_media": math.fsum(media_caso) / len(media_caso),
            "acerto_caso_rep_min": min(rep_acc), "acerto_caso_rep_max": max(rep_acc),
            "ic95_baixo": ic[0], "ic95_alto": ic[1],
            "acerto_por_caso": {c: math.fsum(v) / len(v) for c, v in sorted(por_caso.items())},
            "acerto_campo": {c: sum(r["avaliacao"]["campos"][c] for r in rs) / len(rs) for c in CAMPOS},
            "acerto_tipo": {t: math.fsum(v) / len(v) for t, v in sorted(por_tipo.items())},
            "json_valido": sum(r["avaliacao"]["json_valido"] for r in rs) / len(rs),
            "schema_valido": sum(r["avaliacao"]["schema_valido"] for r in rs) / len(rs),
            "truncadas": sum(1 for r in rs if r.get("stop_reason") not in (None, "end_turn")),
            "tokens_entrada_media": sum(r["tokens_entrada"] for r in rs) / len(rs),
            "tokens_saida_media": sum(r["tokens_saida"] for r in rs) / len(rs),
            "custo_total_usd": custo, "custo_por_caso_usd": custo / len(rs),
            "custo_por_acerto_usd": (custo / acertos) if acertos else None,
            "latencia_media_s": math.fsum(lat) / len(lat), "latencia_mediana_s": mediana(lat),
        }
    return saida


def teste_sinal_exato(a_vals, b_vals):
    """Teste do sinal exato, bilateral, pareado por caso. Ignora empates.

    -> (casos a favor de A, casos a favor de B, p). Sob a hipótese de nenhuma diferença, cada caso discordante
    favorece A ou B com probabilidade 1/2."""
    fa = sum(1 for x, y in zip(a_vals, b_vals) if x > y)
    fb = sum(1 for x, y in zip(a_vals, b_vals) if x < y)
    n = fa + fb
    if n == 0:
        return fa, fb, 1.0
    k = min(fa, fb)
    return fa, fb, min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def comparacoes(resumo):
    """Todos os pares de técnicas: (A, B, casos a favor de A, casos a favor de B, p do teste do sinal exato)."""
    ids = sorted(resumo)
    saida = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            ca, cb = resumo[a]["acerto_por_caso"], resumo[b]["acerto_por_caso"]
            casos = sorted(ca)
            fa, fb, p = teste_sinal_exato([ca[c] for c in casos], [cb[c] for c in casos])
            saida.append((a, b, fa, fb, p))
    return saida


ALFA = 0.05


def separaveis(resumo):
    """Pares de técnicas que podem ser declarados diferentes, (melhor, pior).

    Critério, definido antes de medir e reforçado depois da auditoria de 2026-11-20: os IC 95% não se sobrepõem
    E o teste do sinal exato pareado por caso dá p < 0,05. O segundo requisito existe porque o bootstrap percentil
    degenera quando uma técnica acerta 100% dos casos (intervalo 100%-100%, largura zero), o que fazia a
    sobreposição de intervalos, sozinha, declarar diferenças que o teste pareado não sustenta."""
    p_par = {(a, b): p for a, b, _, _, p in comparacoes(resumo)}
    pares = []
    ids = sorted(resumo)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            A, B = resumo[a], resumo[b]
            if p_par[(a, b)] >= ALFA:
                continue
            if A["ic95_baixo"] > B["ic95_alto"]:
                pares.append((a, b))
            elif B["ic95_baixo"] > A["ic95_alto"]:
                pares.append((b, a))
    return pares  # (melhor, pior)


def pct(x):
    return f"{100 * x:.1f}%"


def relatorio(resumo, gasto_total):
    L = ["# Resultados medidos", "",
         "Gerado por `python src/analisar.py`. Cada número vem dos arquivos brutos; o método está no cabeçalho de `src/analisar.py`.", "",
         "| Técnica | Prompt | Acerto por caso (média) | IC 95% | Mín–máx entre repetições | JSON válido | Custo por caso (US$) | Custo por acerto (US$) | Latência média / mediana (s) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for tid, r in resumo.items():
        cpa = f"{r['custo_por_acerto_usd']:.6f}" if r["custo_por_acerto_usd"] is not None else "n/a"
        L.append(f"| {tid} {r['tecnica']} | {r['prompt_versao']} `{r['prompt_hash12']}` | {pct(r['acerto_caso_media'])} | "
                 f"{pct(r['ic95_baixo'])}–{pct(r['ic95_alto'])} | {pct(r['acerto_caso_rep_min'])}–{pct(r['acerto_caso_rep_max'])} | "
                 f"{pct(r['json_valido'])} | {r['custo_por_caso_usd']:.6f} | {cpa} | {r['latencia_media_s']:.2f} / {r['latencia_mediana_s']:.2f} |")
    L += ["", "## Quem pode ser declarado melhor", "",
          "Critério: os intervalos de 95% não se sobrepõem **e** o teste do sinal exato pareado por caso dá p < 0,05. "
          "O segundo requisito existe porque o bootstrap devolve um intervalo de largura zero (100%–100%) quando uma técnica acerta todos os casos.", ""]
    par = separaveis(resumo)
    if par:
        L += [f"- {a} ({NOMES.get(a, a)}) > {b} ({NOMES.get(b, b)}): intervalos sem sobreposição e p < 0,05." for a, b in par]
    else:
        L += ["- Nenhuma técnica pode ser declarada melhor: nenhum par atende aos dois requisitos."]
    L += ["", "### Comparações pareadas (teste do sinal exato, bilateral)", "",
          "| Par | Casos a favor do primeiro | Casos a favor do segundo | Empates | p |", "|---|---|---|---|---|"]
    n_casos = len(next(iter(resumo.values()))["acerto_por_caso"])
    for a, b, fa, fb, p in comparacoes(resumo):
        L.append(f"| {a} × {b} | {fa} | {fb} | {n_casos - fa - fb} | {p:.3f} |")
    L += ["", "Cada caso conta uma vez, com o acerto médio das repetições; casos em que as duas técnicas têm o mesmo acerto são empates e saem do teste."]
    L += ["", "## Acerto por campo", "", "| Campo | " + " | ".join(resumo) + " |", "|---|" + "---|" * len(resumo)]
    for c in CAMPOS:
        L.append(f"| {c} | " + " | ".join(pct(r["acerto_campo"][c]) for r in resumo.values()) + " |")
    tipos = sorted({t for r in resumo.values() for t in r["acerto_tipo"]})
    L += ["", "## Acerto por tipo de caso", "", "| Tipo | " + " | ".join(resumo) + " |", "|---|" + "---|" * len(resumo)]
    for t in tipos:
        L.append(f"| {t} | " + " | ".join(pct(r["acerto_tipo"].get(t, 0)) for r in resumo.values()) + " |")
    L += ["", "## Tokens e respostas cortadas", "", "| Técnica | Tokens de entrada (média) | Tokens de saída (média) | Respostas cortadas |", "|---|---|---|---|"]
    for tid, r in resumo.items():
        L.append(f"| {tid} | {r['tokens_entrada_media']:.0f} | {r['tokens_saida_media']:.0f} | {r['truncadas']} |")
    L += ["", f"Custo total das respostas analisadas: US$ {sum(r['custo_total_usd'] for r in resumo.values()):.6f}."]
    if gasto_total is not None:
        L.append(f"Gasto acumulado do projeto (piloto + rodada completa, livro-caixa do cliente): US$ {gasto_total:.6f} de US$ 1,00.")
    return "\n".join(L) + "\n"


def main():
    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else caminhos.RESULTADOS / "brutos"
    regs = carregar(pasta)
    if not regs:
        sys.exit(f"Nenhum resultado em {pasta}")
    resumo = resumir(regs)
    gasto = None
    g = RAIZ / "logs" / "gasto.json"
    if g.exists():
        gasto = json.loads(g.read_text(encoding="utf-8"))["gasto_usd"]
    caminhos.RESULTADOS.mkdir(parents=True, exist_ok=True)
    (caminhos.RESULTADOS / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (caminhos.RESULTADOS / "RELATORIO.md").write_text(relatorio(resumo, gasto), encoding="utf-8", newline="\n")
    print((caminhos.RESULTADOS / "RELATORIO.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
