# Resultados medidos

Gerado por `python src/analisar.py`. Cada número vem dos arquivos brutos; o método está no cabeçalho de `src/analisar.py`.

| Técnica | Prompt | Acerto por caso (média) | IC 95% | Mín–máx entre repetições | JSON válido | Custo por caso (US$) | Custo por acerto (US$) | Latência média / mediana (s) |
|---|---|---|---|---|---|---|---|---|
| T1 zero-shot | v1 `1ef67d6a52fc` | 98.7% | 96.7%–100.0% | 96.0%–100.0% | 100.0% | 0.000125 | 0.000127 | 1.42 / 1.33 |
| T2 few-shot | v1 `be0e8998a563` | 92.7% | 84.7%–98.7% | 92.0%–94.0% | 100.0% | 0.000163 | 0.000176 | 1.31 / 1.10 |
| T3 chain-of-thought | v1 `b3a7a7a94ceb` | 100.0% | 100.0%–100.0% | 100.0%–100.0% | 100.0% | 0.000351 | 0.000351 | 3.29 / 3.21 |
| T4 system prompt | v1 `bb14abcde430` | 92.0% | 84.0%–98.0% | 92.0%–92.0% | 100.0% | 0.000160 | 0.000174 | 1.51 / 1.24 |

## Quem pode ser declarado melhor

Critério: os intervalos de 95% não se sobrepõem **e** o teste do sinal exato pareado por caso dá p < 0,05. O segundo requisito existe porque o bootstrap devolve um intervalo de largura zero (100%–100%) quando uma técnica acerta todos os casos.

- Nenhuma técnica pode ser declarada melhor: nenhum par atende aos dois requisitos.

### Comparações pareadas (teste do sinal exato, bilateral)

| Par | Casos a favor do primeiro | Casos a favor do segundo | Empates | p |
|---|---|---|---|---|
| T1 × T2 | 4 | 0 | 46 | 0.125 |
| T1 × T3 | 0 | 2 | 48 | 0.500 |
| T1 × T4 | 4 | 0 | 46 | 0.125 |
| T2 × T3 | 0 | 4 | 46 | 0.125 |
| T2 × T4 | 1 | 0 | 49 | 1.000 |
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
| valor_unitario | 98.7% | 92.7% | 100.0% | 92.0% |
| moeda | 100.0% | 99.3% | 100.0% | 96.7% |
| fornecedor | 100.0% | 100.0% | 100.0% | 100.0% |

## Acerto por tipo de caso

| Tipo | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
| campos_faltando | 100.0% | 100.0% | 100.0% | 100.0% |
| completa | 100.0% | 100.0% | 100.0% | 100.0% |
| correcao | 100.0% | 100.0% | 100.0% | 100.0% |
| data_formato | 100.0% | 100.0% | 100.0% | 100.0% |
| data_relativa | 100.0% | 100.0% | 100.0% | 100.0% |
| duas_quantidades | 100.0% | 100.0% | 100.0% | 100.0% |
| email_longo | 100.0% | 100.0% | 100.0% | 100.0% |
| fornecedor_apelido | 100.0% | 100.0% | 100.0% | 100.0% |
| moeda_extenso | 100.0% | 100.0% | 100.0% | 100.0% |
| moeda_simbolo | 100.0% | 100.0% | 100.0% | 100.0% |
| numero_extenso | 100.0% | 100.0% | 100.0% | 100.0% |
| ruido | 100.0% | 100.0% | 100.0% | 100.0% |
| unidades_variadas | 100.0% | 100.0% | 100.0% | 100.0% |
| valor_br | 100.0% | 100.0% | 100.0% | 100.0% |
| valor_total | 83.3% | 8.3% | 100.0% | 0.0% |

## Tokens e respostas cortadas

| Técnica | Tokens de entrada (média) | Tokens de saída (média) | Respostas cortadas |
|---|---|---|---|
| T1 | 309 | 188 | 0 |
| T2 | 863 | 154 | 0 |
| T3 | 358 | 631 | 0 |
| T4 | 715 | 177 | 0 |

Custo total das respostas analisadas: US$ 0.119941.
Gasto acumulado do projeto (piloto + rodada completa, livro-caixa do cliente): US$ 0.227230 de US$ 1,00.
