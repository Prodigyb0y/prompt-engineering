"""Gera a v3 dos dados fictícios: 20 casos NOVOS para validar o T4 v2 (seed 3003) em dados/extracao/v3/.

Por que existe: o T4 v2 foi escrito olhando os casos v2 (a regra do valor total saiu do que a v1 errou neles).
Os 50 casos v2 são, portanto, casos de desenvolvimento dessa regra. Estes 20 casos nunca foram vistos antes da
escrita do prompt nem durante ela: o gabarito é gerado e congelado (SHA-256) ANTES de qualquer chamada à API.

Os modelos de frase e as regras de rotulagem são os da v2 (gerar_dados_v2.montar); muda a semente, os ids (H01 a H20)
e a mistura de tipos: bastante valor_total (onde a regra nova atua) e todos os outros tipos novos da v2, para
medir também regressão. Nenhum texto repete caso v1, caso v2 ou exemplo few-shot (checado aqui e na validação).

Uso: python src/gerar_dados_v3.py
"""
import json
import random

import gerar_dados as g1
import gerar_dados_v2 as g2

SEED = 3003
SAIDA = g1.DADOS.parent / "v3"
TIPOS = [("valor_total", 6), ("correcao", 3), ("numero_extenso", 2), ("moeda_extenso", 2), ("email_longo", 2),
         ("campos_faltando", 2), ("completa", 1), ("data_relativa", 1), ("valor_br", 1)]
N = 20


def _textos_existentes():
    v1 = json.loads((g1.DADOS / "casos_teste.json").read_text(encoding="utf-8"))
    v2 = json.loads((g1.DADOS.parent / "v2" / "casos_teste.json").read_text(encoding="utf-8"))
    fewshot = json.loads((g1.DADOS / "exemplos_fewshot.json").read_text(encoding="utf-8"))
    return {c["texto"] for c in v1} | {c["texto"] for c in v2} | {e["entrada"] for e in fewshot}


def gerar():
    rng = random.Random(SEED)
    usados = set()
    ja = _textos_existentes()
    casos, gabarito, fonte = [], {}, {}
    n = 0
    for tipo, qtd in TIPOS:
        for _ in range(qtd):
            for _tentativa in range(200):   # refaz o sorteio se o texto repetir algo que já existe
                estado = rng.getstate()
                gab, texto, trechos, meta = g2.montar(rng, tipo, usados)
                if texto not in ja and texto not in {c["texto"] for c in casos}:
                    break
            else:
                raise RuntimeError(f"não consegui gerar um caso novo do tipo {tipo}")
            n += 1
            cid = f"H{n:02d}"
            casos.append({"id": cid, "tipo": tipo, "texto": texto})
            gabarito[cid] = gab
            fonte[cid] = {"tipo": tipo, "registro": gab, "trechos": trechos, "extras": meta}
    assert len(casos) == N == sum(q for _, q in TIPOS)
    rng.shuffle(casos)
    return casos, gabarito, fonte


def main():
    casos, gabarito, fonte = gerar()
    SAIDA.mkdir(parents=True, exist_ok=True)
    for nome, obj in [("casos_teste.json", casos), ("gabarito.json", gabarito), ("registros_fonte.json", fonte)]:
        (SAIDA / nome).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"v3 gerada: {len(casos)} casos em {SAIDA} (seed {SEED}). Próximo: validar_dados_v3.py --congelar.")


if __name__ == "__main__":
    main()
