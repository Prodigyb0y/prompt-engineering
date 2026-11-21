"""Compara o prompt T4 v1 com o T4 v2 nos dados v2 e gera resultados/v2/ITERACAO.md.

O T4 v2 foi escrito depois de ver o resultado da v1 nos casos de valor_total (D33-D36). Portanto estes 50 casos
funcionam como casos de DESENVOLVIMENTO para essa mudança: o resultado mostra se a correção funcionou e se
quebrou outra coisa (regressão), mas não prova que ela vale para casos novos.

Uso: PE_VERSAO=v2 python src/comparar_iteracao.py   (depois de PE_VERSAO=v2 python src/rodar.py --iteracao)
"""
import collections
import difflib
import json
import math
import sys

import caminhos
import prompts_lib
from analisar import carregar, teste_sinal_exato
import validador


def _media(xs):
    return math.fsum(xs) / len(xs) if xs else 0.0


def comparar(base, nova, casos):
    """base e nova: listas de respostas brutas do T4 (v1 e v2). -> dict com contagens por tipo, geral e regressões."""
    tipo = {c["id"]: c["tipo"] for c in casos}
    def agrupar(regs):
        por_caso = collections.defaultdict(list)
        for r in regs:
            por_caso[r["caso"]].append(1.0 if r["avaliacao"]["caso_correto"] else 0.0)
        return por_caso
    b, n = agrupar(base), agrupar(nova)
    ids = sorted(set(b) & set(n))
    por_tipo = collections.OrderedDict()
    for t in sorted({tipo[i] for i in ids}):
        cs = [i for i in ids if tipo[i] == t]
        por_tipo[t] = {"casos": len(cs),
                       "respostas": sum(len(b[i]) for i in cs) , "certas_v1": int(sum(sum(b[i]) for i in cs)),
                       "certas_v2": int(sum(sum(n[i]) for i in cs)), "respostas_v2": sum(len(n[i]) for i in cs)}
    melhorou = [i for i in ids if _media(n[i]) > _media(b[i])]
    piorou = [i for i in ids if _media(n[i]) < _media(b[i])]
    _, _, p_sinal = teste_sinal_exato([_media(n[i]) for i in ids], [_media(b[i]) for i in ids])
    return {"casos": len(ids), "por_tipo": por_tipo,
            "acerto_v1": _media([_media(b[i]) for i in ids]), "acerto_v2": _media([_media(n[i]) for i in ids]),
            "custo_v1": _media([r["custo_usd"] for r in base]), "custo_v2": _media([r["custo_usd"] for r in nova]),
            "tokens_saida_v1": _media([r["tokens_saida"] for r in base]), "tokens_saida_v2": _media([r["tokens_saida"] for r in nova]),
            "melhorou": melhorou, "piorou": piorou, "p_sinal": p_sinal}


def reavaliar(regs, gabarito, tecnica="T4"):
    """Reaplica o validador às respostas brutas; devolve quantas avaliações gravadas divergem da recalculada."""
    return sum(1 for r in regs if validador.avaliar(r["resposta"], gabarito[r["caso"]], tecnica)["caso_correto"] != r["avaliacao"]["caso_correto"])


def relatorio(c, diff, divergencias=None):
    pct = lambda x: f"{100 * x:.1f}%"
    L = ["# Iteração de prompt: T4 v1 → T4 v2 (dados v2)", "",
         "Gerado por `python src/comparar_iteracao.py`. O T4 v2 foi escrito **depois** de ver o resultado da v1 nos casos de `valor_total`; "
         "por isso estes 50 casos são de desenvolvimento para essa mudança. O resultado mostra se a correção funcionou e se quebrou outra coisa, "
         "não prova que ela vale para casos novos.", "",
         "## O que mudou no prompt", "", "```diff", *diff, "```", "",
         "## Resultado", "",
         f"- Acerto por caso (média de 3 repetições, {c['casos']} casos): v1 {pct(c['acerto_v1'])}, v2 {pct(c['acerto_v2'])}.",
         f"- Custo médio por resposta (US$): v1 {c['custo_v1']:.6f}, v2 {c['custo_v2']:.6f}. Tokens de saída médios: v1 {c['tokens_saida_v1']:.0f}, v2 {c['tokens_saida_v2']:.0f}.", "",
         "| Tipo de caso | Casos | Respostas certas v1 | Respostas certas v2 |", "|---|---|---|---|"]
    for t, x in c["por_tipo"].items():
        L.append(f"| {t} | {x['casos']} | {x['certas_v1']} de {x['respostas']} | {x['certas_v2']} de {x['respostas_v2']} |")
    L += ["", "## Regressões", "",
          ("Casos em que o v2 acertou menos que o v1: " + ", ".join(c["piorou"]) + ".") if c["piorou"] else "Nenhum caso piorou com o v2.",
          ("Casos em que o v2 acertou mais que o v1: " + ", ".join(c["melhorou"]) + ".") if c["melhorou"] else "Nenhum caso melhorou com o v2.", "",
          f"Teste do sinal exato pareado por caso (bilateral): {len(c['melhorou'])} casos melhoraram, {len(c['piorou'])} pioraram, p = {c['p_sinal']:.3f}. "
          "Com poucos casos discordantes o teste não chega a p < 0,05 mesmo quando todos vão na mesma direção; o efeito aqui está concentrado num único tipo de caso.", ""]
    if divergencias is not None:
        L += ["## Verificação", "", f"Reavaliação das respostas brutas com o validador: {divergencias} divergências em relação à avaliação gravada.", ""]
    return "\n".join(L)


def diff_prompts():
    a = prompts_lib.carregar("T4", "v1")["system"].splitlines()
    b = prompts_lib.carregar("T4", "v2")["system"].splitlines()
    return [l for l in difflib.unified_diff(a, b, "T4 v1", "T4 v2", lineterm="", n=0) if not l.startswith("@@")]


def main():
    if caminhos.VERSAO != "v2":
        sys.exit("Rode com PE_VERSAO=v2.")
    casos = json.loads((caminhos.DADOS / "casos_teste.json").read_text(encoding="utf-8"))
    base = [r for r in carregar(caminhos.RESULTADOS / "brutos") if r["tecnica"] == "T4"]
    nova = carregar(caminhos.RESULTADOS / "iteracao" / "brutos")
    if not nova:
        sys.exit("Sem respostas do T4 v2: rode antes PE_VERSAO=v2 python src/rodar.py --iteracao")
    c = comparar(base, nova, casos)
    gab = json.loads((caminhos.DADOS / "gabarito.json").read_text(encoding="utf-8"))
    texto = relatorio(c, diff_prompts(), reavaliar(nova, gab))
    (caminhos.RESULTADOS / "ITERACAO.md").write_text(texto + "\n", encoding="utf-8", newline="\n")
    (caminhos.RESULTADOS / "iteracao.json").write_text(json.dumps({**c, "diff": diff_prompts()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(texto)


if __name__ == "__main__":
    main()
