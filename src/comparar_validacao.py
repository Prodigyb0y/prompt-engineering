"""Validação do T4 v2 em 20 casos novos (dados/extracao/v3). Gera resultados/extracao/v3/VALIDACAO.md e validacao.json.

Pergunta: as duas linhas novas do T4 v2 (regra do valor total) valem para casos que o autor não viu quando as escreveu,
e o v2 continua acertando o resto?

Critério escrito ANTES de rodar (não muda depois de ver o resultado):
- A regra "generaliza" se o v2 acertar pelo menos 17 das 18 respostas dos 6 casos novos de valor_total (3 repetições).
- Há "regressão" se, nos casos que não são de valor_total, o v2 acertar menos respostas que o v1.
Qualquer outro resultado é publicado como saiu, com o que ele ensina.

Os casos são 20: o resultado dá indício, não uma garantia (ver Limitações).

Uso: PE_VERSAO=v3 python src/comparar_validacao.py   (depois de PE_VERSAO=v3 python src/rodar.py --validacao)
"""
import collections
import json
import sys

import caminhos
import comparar_iteracao as ci
from analisar import carregar

LIMITE_GENERALIZA = 17   # de 18 respostas de valor_total
CAMPOS = ["solicitante_area", "item", "quantidade", "unidade", "prazo_entrega", "valor_unitario", "moeda", "fornecedor"]


def erros_do_v2(regs, gabarito):
    """Uma linha por resposta errada: caso, tipo, repetição e os campos que divergem."""
    saida = []
    for r in sorted(regs, key=lambda r: (r["caso"], r["repeticao"])):
        if r["avaliacao"]["caso_correto"]:
            continue
        campos = [c for c, ok in r["avaliacao"].get("campos", {}).items() if not ok]
        saida.append({"caso": r["caso"], "tipo": r["tipo"], "repeticao": r["repeticao"], "campos_errados": campos,
                      "json_valido": r["avaliacao"].get("json_valido")})
    return saida


def veredito(c):
    vt = c["por_tipo"].get("valor_total")
    resto_v1 = sum(x["certas_v1"] for t, x in c["por_tipo"].items() if t != "valor_total")
    resto_v2 = sum(x["certas_v2"] for t, x in c["por_tipo"].items() if t != "valor_total")
    resto_n = sum(x["respostas_v2"] for t, x in c["por_tipo"].items() if t != "valor_total")
    return {"valor_total_certas_v1": vt["certas_v1"], "valor_total_certas_v2": vt["certas_v2"], "valor_total_respostas": vt["respostas_v2"],
            "generaliza": vt["certas_v2"] >= LIMITE_GENERALIZA,
            "resto_certas_v1": resto_v1, "resto_certas_v2": resto_v2, "resto_respostas": resto_n,
            "regressao": resto_v2 < resto_v1}


def relatorio(c, v, erros, diff, divergencias):
    pct = lambda x: f"{100 * x:.1f}%".replace(".", ",")
    L = ["# Validação do T4 v2 em 20 casos novos", "",
         "Gerado por `PE_VERSAO=v3 python src/comparar_validacao.py`. Os 20 casos (H01 a H20) foram gerados e congelados por hash antes de qualquer chamada. "
         "O T4 v2 foi escrito olhando os casos da v2; estes casos nunca foram vistos por quem escreveu o prompt.", "",
         "## Critério (escrito antes de rodar)", "",
         f"- A regra generaliza se o v2 acertar ao menos {LIMITE_GENERALIZA} das {v['valor_total_respostas']} respostas dos casos de valor total.",
         "- Há regressão se, nos outros casos, o v2 acertar menos respostas que o v1.", "",
         "## Resultado", "",
         f"- Acerto por caso (média de 3 repetições, {c['casos']} casos): v1 {pct(c['acerto_v1'])}, v2 {pct(c['acerto_v2'])}.",
         f"- Valor total: v1 {v['valor_total_certas_v1']} de {v['valor_total_respostas']}, v2 {v['valor_total_certas_v2']} de {v['valor_total_respostas']} → "
         f"{'a regra generalizou' if v['generaliza'] else 'a regra NÃO generalizou pelo critério'}.",
         f"- Demais tipos: v1 {v['resto_certas_v1']} de {v['resto_respostas']}, v2 {v['resto_certas_v2']} de {v['resto_respostas']} → "
         f"{'houve regressão' if v['regressao'] else 'sem regressão'}.",
         f"- Custo médio por resposta (US$): v1 {c['custo_v1']:.6f}, v2 {c['custo_v2']:.6f}. Tokens de saída médios: v1 {c['tokens_saida_v1']:.0f}, v2 {c['tokens_saida_v2']:.0f}.", "",
         "| Tipo de caso | Casos | Respostas certas v1 | Respostas certas v2 |", "|---|---|---|---|"]
    for t, x in c["por_tipo"].items():
        L.append(f"| {t} | {x['casos']} | {x['certas_v1']} de {x['respostas']} | {x['certas_v2']} de {x['respostas_v2']} |")
    L += ["", "## Respostas erradas do v2", ""]
    if erros:
        L += ["| Caso | Tipo | Repetição | Campos errados |", "|---|---|---|---|"]
        L += [f"| {e['caso']} | {e['tipo']} | {e['repeticao']} | {', '.join(e['campos_errados']) or 'JSON inválido ou fora do schema'} |" for e in erros]
    else:
        L.append("Nenhuma resposta errada.")
    L += ["", "## O que mudou no prompt (v1 → v2)", "", "```diff", *diff, "```", "",
          "## Verificação", "", f"Reavaliação das respostas brutas do v2 com o validador: {divergencias} divergências em relação à avaliação gravada.", ""]
    return "\n".join(L)


def main():
    if caminhos.VERSAO != "v3":
        sys.exit("Rode com PE_VERSAO=v3.")
    casos = json.loads((caminhos.DADOS / "casos_teste.json").read_text(encoding="utf-8"))
    gab = json.loads((caminhos.DADOS / "gabarito.json").read_text(encoding="utf-8"))
    base = carregar(caminhos.RESULTADOS / "brutos" / "v1")
    nova = carregar(caminhos.RESULTADOS / "brutos" / "v2")
    if not base or not nova:
        sys.exit("Sem respostas: rode antes PE_VERSAO=v3 python src/rodar.py --validacao")
    c = ci.comparar(base, nova, casos)
    v = veredito(c)
    erros = erros_do_v2(nova, gab)
    diff = ci.diff_prompts()
    div = ci.reavaliar(nova, gab) + ci.reavaliar(base, gab)
    (caminhos.RESULTADOS / "VALIDACAO.md").write_text(relatorio(c, v, erros, diff, div) + "\n", encoding="utf-8", newline="\n")
    (caminhos.RESULTADOS / "validacao.json").write_text(json.dumps({**c, "veredito": v, "erros_v2": erros, "diff": diff, "divergencias": div,
                                                                     "respostas_v1": len(base), "respostas_v2": len(nova), "completo": len(base) == len(nova) == 60},
                                                                    ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(relatorio(c, v, erros, diff, div))


if __name__ == "__main__":
    main()
