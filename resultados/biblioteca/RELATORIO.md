# Relatório das rodadas novas (P2 a P5)

Gerado por `src/analisar_biblioteca.py` a partir de `resultados/biblioteca/brutos/`. Nenhum número foi digitado à mão.

Gasto novo: US$ 0,085039 (piloto US$ 0,003544; rodadas US$ 0,081495).

| Experimento | Variante | Acerto (média) | Mín–máx entre repetições | Custo por resposta (US$) | Custo por acerto (US$) | Latência média (s) | Respostas |
|---|---|---|---|---|---|---|---|
| E3 | Zero-shot | 91,7% | 90,0%–95,0% | 0,000073 | 0,000080 | 0,97 | 60 |
| E3 | Few-shot | 98,3% | 95,0%–100,0% | 0,000137 | 0,000140 | 0,95 | 60 |
| E4 | Encadeado (P1 → P3) | 78,3% | 75,0%–80,0% | 0,000256 | 0,000327 | 2,18 | 60 |
| E4 | Prompt único (extrai e escreve) | 81,7% | 75,0%–85,0% | 0,000270 | 0,000331 | 2,28 | 60 |
| P4 | Saída estruturada | 95,0% | 90,0%–100,0% | 0,000219 | 0,000231 | 1,67 | 60 |
| E5 | Sem raciocínio | 95,0% | 95,0%–95,0% | 0,000123 | 0,000130 | 1,06 | 60 |
| E5 | Com raciocínio (chain-of-thought) | 100,0% | 100,0%–100,0% | 0,000278 | 0,000278 | 2,01 | 60 |
| E6 | Encadeado com e-mail v2 (P1 → P3 v2) | não medido | — | — | — | — | 0 |

## Comparações pareadas (teste do sinal exato, empates excluídos)

| Experimento | Base | Alternativa | Casos a favor da base | Casos a favor da alternativa | p |
|---|---|---|---|---|---|
| E3 | Zero-shot | Few-shot | 1 | 2 | 1,000 |
| E4 | Prompt único (extrai e escreve) | Encadeado (P1 → P3) | 6 | 4 | 0,754 |
| E5 | Sem raciocínio | Com raciocínio (chain-of-thought) | 0 | 1 | 1,000 |
| E6 | Encadeado com e-mail v1 (P1 → P3 v1) | Encadeado com e-mail v2 (P1 → P3 v2) | — | — | não medido |
