# Validação do T4 v2 em 20 casos novos

Gerado por `PE_VERSAO=v3 python src/comparar_validacao.py`. Os 20 casos (H01 a H20) foram gerados e congelados por hash antes de qualquer chamada. O T4 v2 foi escrito olhando os casos da v2; estes casos nunca foram vistos por quem escreveu o prompt.

## Critério (escrito antes de rodar)

- A regra generaliza se o v2 acertar ao menos 17 das 18 respostas dos casos de valor total.
- Há regressão se, nos outros casos, o v2 acertar menos respostas que o v1.

## Resultado

- Acerto por caso (média de 3 repetições, 20 casos): v1 70,0%, v2 100,0%.
- Valor total: v1 0 de 18, v2 18 de 18 → a regra generalizou.
- Demais tipos: v1 42 de 42, v2 42 de 42 → sem regressão.
- Custo médio por resposta (US$): v1 0.000194, v2 0.000152. Tokens de saída médios: v1 246, v2 148.

| Tipo de caso | Casos | Respostas certas v1 | Respostas certas v2 |
|---|---|---|---|
| campos_faltando | 2 | 6 de 6 | 6 de 6 |
| completa | 1 | 3 de 3 | 3 de 3 |
| correcao | 3 | 9 de 9 | 9 de 9 |
| data_relativa | 1 | 3 de 3 | 3 de 3 |
| email_longo | 2 | 6 de 6 | 6 de 6 |
| moeda_extenso | 2 | 6 de 6 | 6 de 6 |
| numero_extenso | 2 | 6 de 6 | 6 de 6 |
| valor_br | 1 | 3 de 3 | 3 de 3 |
| valor_total | 6 | 0 de 18 | 18 de 18 |

## Respostas erradas do v2

Nenhuma resposta errada.

## O que mudou no prompt (v1 → v2)

```diff
--- T4 v1
+++ T4 v2
-- moeda vem do símbolo: R$ = "BRL", US$ = "USD", € = "EUR". Sem valor no texto, valor_unitario e moeda são null.
+- moeda vem do símbolo: R$ = "BRL", US$ = "USD", € = "EUR". Sem nenhum valor no texto (nem unitário, nem total), valor_unitario e moeda são null.
+- Se o texto trouxer só o valor total, e não o valor unitário, divida o total pela quantidade para obter valor_unitario. A moeda é a do total.
```

## Verificação

Reavaliação das respostas brutas do v2 com o validador: 0 divergências em relação à avaliação gravada.

