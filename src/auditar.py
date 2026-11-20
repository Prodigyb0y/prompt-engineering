"""Auditoria independente dos resultados: recalcula tudo a partir das respostas brutas.

Não usa resumo.json para calcular nada; só o lê no fim, para comparar. Gera AUDITORIA.md na pasta de
resultados da rodada (PE_VERSAO=v1|v2).

Verificações:
1. Integridade: respostas, combinações únicas (técnica, caso, repetição), stop_reason, retries.
2. Reavaliação: reaplica o validador às respostas brutas e compara com a avaliação gravada.
3. Recálculo do acerto por caso e do custo, comparados com resumo.json.
4. Poder de discriminação: em quantos casos as técnicas diferem.
5. Diversidade dos dados: itens, fornecedores, aberturas de texto.
6. Sobreposição com os exemplos do few-shot (itens e fornecedores iguais aos dos casos de teste).
7. Casos por tipo.

Uso: python src/auditar.py
"""
import collections
import json
import re
import statistics

import caminhos
import custo as custo_mod
import validador as v
from analisar import carregar

RAIZ = caminhos.RAIZ


def molde(texto):
    return re.sub(r"\d+[.,\d]*", "#", texto)[:28]


def main():
    regs = carregar(caminhos.RESULTADOS / "brutos")
    if not regs:
        raise SystemExit("Sem respostas brutas locais: a auditoria precisa delas.")
    gab = json.loads((caminhos.DADOS / "gabarito.json").read_text(encoding="utf-8"))
    casos = json.loads((caminhos.DADOS / "casos_teste.json").read_text(encoding="utf-8"))
    resumo = json.loads((caminhos.RESULTADOS / "resumo.json").read_text(encoding="utf-8"))
    fewshot = json.loads((RAIZ / "dados" / "extracao" / "v1" / "exemplos_fewshot.json").read_text(encoding="utf-8"))
    precos = custo_mod.carregar_precos()
    tecs = sorted({r["tecnica"] for r in regs})

    L = [f"# Auditoria independente ({caminhos.VERSAO})", "",
         "Gerado por `python src/auditar.py`. Recalcula os números a partir das respostas brutas, sem usar `resumo.json`, e só depois compara.", ""]

    # 1 integridade
    comb = {(r["tecnica"], r["caso"], r["repeticao"]) for r in regs}
    L += ["## 1. Integridade", "", f"- Respostas: {len(regs)}; combinações únicas (técnica, caso, repetição): {len(comb)}.",
          f"- `stop_reason`: {dict(collections.Counter(r['stop_reason'] for r in regs))}.",
          f"- Respostas com mais de uma tentativa: {sum(1 for r in regs if r['tentativas'] > 1)}.", ""]

    # 2 reavaliação
    dif = sum(1 for r in regs if v.avaliar(r["resposta"], gab[r["caso"]], r["tecnica"])["campos"] != r["avaliacao"]["campos"]
              or v.avaliar(r["resposta"], gab[r["caso"]], r["tecnica"])["caso_correto"] != r["avaliacao"]["caso_correto"])
    L += ["## 2. Reavaliação com o validador", "", f"- Respostas em que a avaliação recalculada difere da gravada: {dif} de {len(regs)}.", ""]

    # 3 recálculo
    por = {t: collections.defaultdict(list) for t in tecs}
    for r in regs:
        por[r["tecnica"]][r["caso"]].append(1.0 if v.avaliar(r["resposta"], gab[r["caso"]], r["tecnica"])["caso_correto"] else 0.0)
    L += ["## 3. Recálculo de acerto e custo", "", "| Técnica | Acerto recalculado | Acerto no resumo | Custo total recalculado (US$) | Custo total no resumo (US$) |", "|---|---|---|---|---|"]
    for t in tecs:
        acerto = statistics.fmean(statistics.fmean(x) for x in por[t].values())
        c = sum(custo_mod.custo_usd(r["tokens_entrada"], r["tokens_saida"], precos) for r in regs if r["tecnica"] == t)
        L.append(f"| {t} | {100 * acerto:.2f}% | {100 * resumo[t]['acerto_caso_media']:.2f}% | {c:.6f} | {resumo[t]['custo_total_usd']:.6f} |")
    L.append("")

    # 4 poder de discriminação
    todos = [c["id"] for c in casos if all(all(x == 1.0 for x in por[t][c["id"]]) for t in tecs)]
    dif_ids = [c["id"] for c in casos if c["id"] not in todos]
    L += ["## 4. Poder de discriminação", "",
          f"- Casos em que todas as técnicas acertaram em todas as repetições: {len(todos)} de {len(casos)}.",
          f"- Casos em que alguma técnica errou alguma vez (os únicos que podem separar técnicas): {len(dif_ids)} ({', '.join(dif_ids)}).",
          f"- Tipos desses casos: {dict(collections.Counter(next(c['tipo'] for c in casos if c['id'] == i) for i in dif_ids))}.", ""]

    # 5 diversidade
    itens = {gab[c["id"]]["item"] for c in casos}
    forn = {gab[c["id"]]["fornecedor"] for c in casos if gab[c["id"]]["fornecedor"]}
    L += ["## 5. Diversidade dos dados", "",
          f"- Itens distintos: {len(itens)}; fornecedores distintos: {len(forn)}; textos distintos: {len({c['texto'] for c in casos})} de {len(casos)}.",
          f"- Aberturas distintas (28 primeiros caracteres, números mascarados): {len({molde(c['texto']) for c in casos})} de {len(casos)}.",
          f"- Tamanho do texto em caracteres (mín / mediana / máx): {min(len(c['texto']) for c in casos)} / {int(statistics.median(len(c['texto']) for c in casos))} / {max(len(c['texto']) for c in casos)}.", ""]

    # 6 sobreposição com few-shot
    it_fs = {x["saida"]["item"] for x in fewshot}
    fo_fs = {x["saida"]["fornecedor"] for x in fewshot if x["saida"]["fornecedor"]}
    L += ["## 6. Sobreposição com os exemplos do few-shot", "",
          f"- Casos de teste com o mesmo item de algum exemplo do T2: {sum(1 for c in casos if gab[c['id']]['item'] in it_fs)} de {len(casos)}.",
          f"- Casos de teste com o mesmo fornecedor de algum exemplo do T2: {sum(1 for c in casos if gab[c['id']]['fornecedor'] in fo_fs)} de {len(casos)}.",
          f"- Textos de teste idênticos aos dos exemplos: {sum(1 for c in casos for x in fewshot if c['texto'] == x['entrada'])}.", ""]

    # 7 casos por tipo
    n_tipo = collections.Counter(c["tipo"] for c in casos)
    L += ["## 7. Casos por tipo", "", f"- Mínimo {min(n_tipo.values())}, mediana {int(statistics.median(n_tipo.values()))}, máximo {max(n_tipo.values())}. Distribuição: {dict(sorted(n_tipo.items()))}.", ""]

    destino = caminhos.RESULTADOS / "AUDITORIA.md"
    destino.write_text("\n".join(L), encoding="utf-8", newline="\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
