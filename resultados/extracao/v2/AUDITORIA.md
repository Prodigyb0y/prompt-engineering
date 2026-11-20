# Auditoria independente (v2)

Gerado por `python src/auditar.py`. Recalcula os números a partir das respostas brutas, sem usar `resumo.json`, e só depois compara.

## 1. Integridade

- Respostas: 600; combinações únicas (técnica, caso, repetição): 600.
- `stop_reason`: {'end_turn': 600}.
- Respostas com mais de uma tentativa: 0.

## 2. Reavaliação com o validador

- Respostas em que a avaliação recalculada difere da gravada: 0 de 600.

## 3. Recálculo de acerto e custo

| Técnica | Acerto recalculado | Acerto no resumo | Custo total recalculado (US$) | Custo total no resumo (US$) |
|---|---|---|---|---|
| T1 | 98.67% | 98.67% | 0.018736 | 0.018736 |
| T2 | 92.67% | 92.67% | 0.024473 | 0.024473 |
| T3 | 100.00% | 100.00% | 0.052715 | 0.052715 |
| T4 | 92.00% | 92.00% | 0.024017 | 0.024017 |

## 4. Poder de discriminação

- Casos em que todas as técnicas acertaram em todas as repetições: 46 de 50.
- Casos em que alguma técnica errou alguma vez (os únicos que podem separar técnicas): 4 (D34, D36, D33, D35).
- Tipos desses casos: {'valor_total': 4}.

## 5. Diversidade dos dados

- Itens distintos: 17; fornecedores distintos: 10; textos distintos: 50 de 50.
- Aberturas distintas (28 primeiros caracteres, números mascarados): 40 de 50.
- Tamanho do texto em caracteres (mín / mediana / máx): 80 / 175 / 405.

## 6. Sobreposição com os exemplos do few-shot

- Casos de teste com o mesmo item de algum exemplo do T2: 7 de 50.
- Casos de teste com o mesmo fornecedor de algum exemplo do T2: 14 de 50.
- Textos de teste idênticos aos dos exemplos: 0.

## 7. Casos por tipo

- Mínimo 2, mediana 3, máximo 6. Distribuição: {'campos_faltando': 3, 'completa': 3, 'correcao': 5, 'data_formato': 3, 'data_relativa': 3, 'duas_quantidades': 2, 'email_longo': 6, 'fornecedor_apelido': 2, 'moeda_extenso': 4, 'moeda_simbolo': 2, 'numero_extenso': 4, 'ruido': 3, 'unidades_variadas': 3, 'valor_br': 3, 'valor_total': 4}.
