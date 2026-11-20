# Classificação dos erros

Gerado por `python src/classificar_erros.py`. Resultado oficial: `RELATORIO.md`. Este arquivo explica os erros dele e traz uma recontagem pós-hoc.

## Erros por classe (número de respostas erradas)

| Classe | T1 zero-shot | T2 few-shot | T3 chain-of-thought | T4 system prompt |
|---|---|---|---|---|
| json_invalido | 0 | 0 | 0 | 0 |
| schema_invalido | 0 | 0 | 0 | 0 |
| fornecedor_ponto_final | 0 | 0 | 0 | 0 |
| valor_nulo_sem_derivar | 2 | 11 | 0 | 12 |
| campo_diferente | 0 | 0 | 0 | 0 |
| total de respostas | 150 | 150 | 150 | 150 |

## Casos com erro

| Caso | Tipo | Erros (técnica: classe, nº de respostas) | Texto |
|---|---|---|---|
| D33 | valor_total | T1: valor_nulo_sem_derivar ×1; T2: valor_nulo_sem_derivar ×3; T4: valor_nulo_sem_derivar ×3 | Oi, preciso de 10 cx de caneta esferográfica (solicitante: RH) – valor total US$ 350,00; Pode ser com a Inform |
| D34 | valor_total | T2: valor_nulo_sem_derivar ×3; T4: valor_nulo_sem_derivar ×3 | Oi, preciso de 20 un de monitor 24 polegadas para a área de Marketing valor total US$ 250,00 – cotação feita c |
| D35 | valor_total | T2: valor_nulo_sem_derivar ×2; T4: valor_nulo_sem_derivar ×3 | Preciso comprar 20 caixas de papel A4 (solicitante: Financeiro); valor total US$ 2400,00; Pode ser com a Tecid |
| D36 | valor_total | T1: valor_nulo_sem_derivar ×1; T2: valor_nulo_sem_derivar ×3; T4: valor_nulo_sem_derivar ×3 | Oi, preciso de 25 caixas de fita adesiva para a área de Manutenção valor total € 222,50; Pode ser com a Químic |

## Recontagem PÓS-HOC (não oficial)

Tolerância: diferença de ponto final no fornecedor ("Ltda." = "Ltda"). Criada depois de ver os resultados, por isso não substitui o resultado oficial. Mesmo método de intervalo (bootstrap, 10.000 reamostragens, seed 42).

| Técnica | Acerto oficial | Acerto pós-hoc | IC 95% pós-hoc |
|---|---|---|---|
| T1 zero-shot | 98.7% | 98.7% | 96.7%–100.0% |
| T2 few-shot | 92.7% | 92.7% | 84.7%–98.7% |
| T3 chain-of-thought | 100.0% | 100.0% | 100.0%–100.0% |
| T4 system prompt | 92.0% | 92.0% | 84.0%–98.0% |

## Recontagem PÓS-HOC sem o tipo `valor_total` (não oficial)

O tipo `valor_total` concentra 25 das 25 respostas erradas. A tabela mostra o acerto nos demais casos. Criada depois de ver os resultados; serve para dizer onde está a diferença, não para trocar o resultado oficial.

| Técnica | Casos | Acerto sem o tipo | IC 95% |
|---|---|---|---|
| T1 zero-shot | 46 | 100.0% | 100.0%–100.0% |
| T2 few-shot | 46 | 100.0% | 100.0%–100.0% |
| T3 chain-of-thought | 46 | 100.0% | 100.0%–100.0% |
| T4 system prompt | 46 | 100.0% | 100.0%–100.0% |
