# Classificação dos erros

Gerado por `python src/classificar_erros.py`. Resultado oficial: `RELATORIO.md`. Este arquivo explica os erros dele e traz uma recontagem pós-hoc.

## Erros por classe (número de respostas erradas)

| Classe | T1 zero-shot | T2 few-shot | T3 chain-of-thought | T4 system prompt |
|---|---|---|---|---|
| json_invalido | 0 | 0 | 0 | 0 |
| schema_invalido | 0 | 0 | 0 | 0 |
| fornecedor_ponto_final | 7 | 3 | 4 | 15 |
| campo_diferente | 0 | 0 | 0 | 0 |
| total de respostas | 150 | 150 | 150 | 150 |

## Casos com erro

| Caso | Tipo | Erros (técnica: classe, nº de respostas) | Texto |
|---|---|---|---|
| C02 | completa | T1: fornecedor_ponto_final ×3; T2: fornecedor_ponto_final ×3; T3: fornecedor_ponto_final ×3; T4: fornecedor_ponto_final ×3 | Preciso comprar 5 cx de papel A4 (solicitante: RH). Cada unidade custa R$ 49,90. Fornecedor: Papelaria Aurora  |
| C13 | campos_faltando | T1: fornecedor_ponto_final ×3; T4: fornecedor_ponto_final ×3 | Oi, preciso de 25 un de toner preto. Valor unitário R$ 35,00. Pode ser com a Papelaria Aurora Ltda. precisa ch |
| C15 | unidades_variadas | T3: fornecedor_ponto_final ×1; T4: fornecedor_ponto_final ×3 | Bom dia! Solicito 50l de óleo lubrificante para a área de Marketing. preço de tabela: R$ 8,90 por unidade. Pod |
| C23 | valor_br | T4: fornecedor_ponto_final ×3 | Bom dia! Solicito 20 m de cabo elétrico 2,5mm para a área de Marketing. Cada unidade custa R$ 1.200,00. cotaçã |
| C45 | ruido | T1: fornecedor_ponto_final ×1; T4: fornecedor_ponto_final ×3 | kkk, Oi, presiso de 25 m de cabo elétrico 2,5mm para a área de Financeiro. preço de tabela: R$ 2450,75 por uni |

## Recontagem PÓS-HOC (não oficial)

Tolerância: diferença de ponto final no fornecedor ("Ltda." = "Ltda"). Criada depois de ver os resultados, por isso não substitui o resultado oficial. Mesmo método de intervalo (bootstrap, 10.000 reamostragens, seed 42).

| Técnica | Acerto oficial | Acerto pós-hoc | IC 95% pós-hoc |
|---|---|---|---|
| T1 zero-shot | 95.3% | 100.0% | 100.0%–100.0% |
| T2 few-shot | 98.0% | 100.0% | 100.0%–100.0% |
| T3 chain-of-thought | 97.3% | 100.0% | 100.0%–100.0% |
| T4 system prompt | 90.0% | 100.0% | 100.0%–100.0% |
