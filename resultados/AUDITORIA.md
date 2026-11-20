# Auditoria independente (v1)

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
| T1 | 95.33% | 95.33% | 0.016269 | 0.016269 |
| T2 | 98.00% | 98.00% | 0.021509 | 0.021509 |
| T3 | 97.33% | 97.33% | 0.049493 | 0.049493 |
| T4 | 90.00% | 90.00% | 0.018892 | 0.018892 |

## 4. Poder de discriminação

- Casos em que todas as técnicas acertaram em todas as repetições: 45 de 50.
- Casos em que alguma técnica errou alguma vez (os únicos que podem separar técnicas): 5 (C13, C45, C15, C23, C02).
- Tipos desses casos: {'campos_faltando': 1, 'ruido': 1, 'unidades_variadas': 1, 'valor_br': 1, 'completa': 1}.

## 5. Diversidade dos dados

- Itens distintos: 17; fornecedores distintos: 11; textos distintos: 50 de 50.
- Aberturas distintas (28 primeiros caracteres, números mascarados): 42 de 50.
- Tamanho do texto em caracteres (mín / mediana / máx): 71 / 163 / 223.

## 6. Sobreposição com os exemplos do few-shot

- Casos de teste com o mesmo item de algum exemplo do T2: 8 de 50.
- Casos de teste com o mesmo fornecedor de algum exemplo do T2: 12 de 50.
- Textos de teste idênticos aos dos exemplos: 0.

## 7. Casos por tipo

- Mínimo 3, mediana 5, máximo 8. Distribuição: {'campos_faltando': 6, 'completa': 8, 'data_formato': 6, 'data_relativa': 4, 'duas_quantidades': 3, 'fornecedor_apelido': 3, 'moeda_simbolo': 5, 'ruido': 3, 'unidades_variadas': 6, 'valor_br': 6}.
