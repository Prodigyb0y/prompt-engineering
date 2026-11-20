# Iteração de prompt: T4 v1 → T4 v2 (dados v2)

Gerado por `python src/comparar_iteracao.py`. O T4 v2 foi escrito **depois** de ver o resultado da v1 nos casos de `valor_total`; por isso estes 50 casos são de desenvolvimento para essa mudança. O resultado mostra se a correção funcionou e se quebrou outra coisa, não prova que ela vale para casos novos.

## O que mudou no prompt

```diff
--- T4 v1
+++ T4 v2
-- moeda vem do símbolo: R$ = "BRL", US$ = "USD", € = "EUR". Sem valor no texto, valor_unitario e moeda são null.
+- moeda vem do símbolo: R$ = "BRL", US$ = "USD", € = "EUR". Sem nenhum valor no texto (nem unitário, nem total), valor_unitario e moeda são null.
+- Se o texto trouxer só o valor total, e não o valor unitário, divida o total pela quantidade para obter valor_unitario. A moeda é a do total.
```

## Resultado

- Acerto por caso (média de 3 repetições, 50 casos): v1 92.0%, v2 100.0%.
- Custo médio por resposta (US$): v1 0.000160, v2 0.000145. Tokens de saída médios: v1 177, v2 133.

| Tipo de caso | Casos | Respostas certas v1 | Respostas certas v2 |
|---|---|---|---|
| campos_faltando | 3 | 9 de 9 | 9 de 9 |
| completa | 3 | 9 de 9 | 9 de 9 |
| correcao | 5 | 15 de 15 | 15 de 15 |
| data_formato | 3 | 9 de 9 | 9 de 9 |
| data_relativa | 3 | 9 de 9 | 9 de 9 |
| duas_quantidades | 2 | 6 de 6 | 6 de 6 |
| email_longo | 6 | 18 de 18 | 18 de 18 |
| fornecedor_apelido | 2 | 6 de 6 | 6 de 6 |
| moeda_extenso | 4 | 12 de 12 | 12 de 12 |
| moeda_simbolo | 2 | 6 de 6 | 6 de 6 |
| numero_extenso | 4 | 12 de 12 | 12 de 12 |
| ruido | 3 | 9 de 9 | 9 de 9 |
| unidades_variadas | 3 | 9 de 9 | 9 de 9 |
| valor_br | 3 | 9 de 9 | 9 de 9 |
| valor_total | 4 | 0 de 12 | 12 de 12 |

## Regressões

Nenhum caso piorou com o v2.
Casos em que o v2 acertou mais que o v1: D33, D34, D35, D36.

Teste do sinal exato pareado por caso (bilateral): 4 casos melhoraram, 0 pioraram, p = 0.125. Com poucos casos discordantes o teste não chega a p < 0,05 mesmo quando todos vão na mesma direção; o efeito aqui está concentrado num único tipo de caso.

## Verificação

Reavaliação das respostas brutas com o validador: 0 divergências em relação à avaliação gravada.

