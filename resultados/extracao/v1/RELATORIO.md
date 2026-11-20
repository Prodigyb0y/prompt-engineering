# Resultados medidos

Gerado por `python src/analisar.py`. Cada número vem dos arquivos brutos; o método está no cabeçalho de `src/analisar.py`.

| Técnica | Prompt | Acerto por caso (média) | IC 95% | Mín–máx entre repetições | JSON válido | Custo por caso (US$) | Custo por acerto (US$) | Latência média / mediana (s) |
|---|---|---|---|---|---|---|---|---|
| T1 zero-shot | v1 `1ef67d6a52fc` | 95.3% | 89.3%–100.0% | 94.0%–96.0% | 100.0% | 0.000108 | 0.000114 | 1.32 / 1.21 |
| T2 few-shot | v1 `be0e8998a563` | 98.0% | 94.0%–100.0% | 98.0%–98.0% | 100.0% | 0.000143 | 0.000146 | 1.14 / 0.97 |
| T3 chain-of-thought | v1 `b3a7a7a94ceb` | 97.3% | 92.7%–100.0% | 96.0%–98.0% | 100.0% | 0.000330 | 0.000339 | 3.17 / 3.06 |
| T4 system prompt | v1 `bb14abcde430` | 90.0% | 82.0%–98.0% | 90.0%–90.0% | 100.0% | 0.000126 | 0.000140 | 1.20 / 1.02 |

## Quem pode ser declarado melhor

Critério: os intervalos de 95% não se sobrepõem **e** o teste do sinal exato pareado por caso dá p < 0,05. O segundo requisito existe porque o bootstrap devolve um intervalo de largura zero (100%–100%) quando uma técnica acerta todos os casos.

- Nenhuma técnica pode ser declarada melhor: nenhum par atende aos dois requisitos.

### Comparações pareadas (teste do sinal exato, bilateral)

| Par | Casos a favor do primeiro | Casos a favor do segundo | Empates | p |
|---|---|---|---|---|
| T1 × T2 | 0 | 2 | 48 | 0.500 |
| T1 × T3 | 1 | 2 | 47 | 1.000 |
| T1 × T4 | 3 | 0 | 47 | 0.250 |
| T2 × T3 | 1 | 0 | 49 | 1.000 |
| T2 × T4 | 4 | 0 | 46 | 0.125 |
| T3 × T4 | 4 | 0 | 46 | 0.125 |

Cada caso conta uma vez, com o acerto médio das repetições; casos em que as duas técnicas têm o mesmo acerto são empates e saem do teste.

## Acerto por campo

| Campo | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
| solicitante_area | 100.0% | 100.0% | 100.0% | 100.0% |
| item | 100.0% | 100.0% | 100.0% | 100.0% |
| quantidade | 100.0% | 100.0% | 100.0% | 100.0% |
| unidade | 100.0% | 100.0% | 100.0% | 100.0% |
| prazo_entrega | 100.0% | 100.0% | 100.0% | 100.0% |
| valor_unitario | 100.0% | 100.0% | 100.0% | 100.0% |
| moeda | 100.0% | 100.0% | 100.0% | 100.0% |
| fornecedor | 95.3% | 98.0% | 97.3% | 90.0% |

## Acerto por tipo de caso

| Tipo | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
| campos_faltando | 83.3% | 100.0% | 100.0% | 83.3% |
| completa | 87.5% | 87.5% | 87.5% | 87.5% |
| data_formato | 100.0% | 100.0% | 100.0% | 100.0% |
| data_relativa | 100.0% | 100.0% | 100.0% | 100.0% |
| duas_quantidades | 100.0% | 100.0% | 100.0% | 100.0% |
| fornecedor_apelido | 100.0% | 100.0% | 100.0% | 100.0% |
| moeda_simbolo | 100.0% | 100.0% | 100.0% | 100.0% |
| ruido | 88.9% | 100.0% | 100.0% | 66.7% |
| unidades_variadas | 100.0% | 100.0% | 94.4% | 83.3% |
| valor_br | 100.0% | 100.0% | 100.0% | 83.3% |

## Tokens e respostas cortadas

| Técnica | Tokens de entrada (média) | Tokens de saída (média) | Respostas cortadas |
|---|---|---|---|
| T1 | 293 | 158 | 0 |
| T2 | 847 | 117 | 0 |
| T3 | 342 | 592 | 0 |
| T4 | 699 | 112 | 0 |

Custo total das respostas analisadas: US$ 0.106163.
Gasto acumulado do projeto (piloto + rodada completa, livro-caixa do cliente): US$ 0.107289 de US$ 1,00.
