# Dados v3: 20 casos novos para validar o T4 v2

Tudo fictício (empresa fictícia Gutenberg Systems). Gerado por `src/gerar_dados_v3.py` (seed 3003), validado por `src/validar_dados_v3.py` e congelado por hash **antes** de qualquer chamada à API.

## Por que existe
O T4 v2 foi escrito olhando os casos da v2: a regra do valor total saiu do que a v1 errou neles (0 de 12 nos quatro casos de valor total). Por isso o 12 de 12 da iteração mostra que a correção funcionou onde foi escrita, mas não prova que ela vale para casos novos. Estes 20 casos nunca foram vistos por quem escreveu o prompt.

## O que tem
- 20 casos (H01 a H20): 6 de valor total, 3 de correção, 2 de número por extenso, 2 de moeda por extenso, 2 de e-mail longo, 2 de campos faltando, 1 completo, 1 de data relativa, 1 de valor em formato brasileiro.
- Mesmos modelos de frase e mesmas regras de rotulagem da v2 (ver `dados/extracao/v2/REVISAO_E_LIMITACOES.md`); muda a semente, os ids e a mistura de tipos.
- Nenhum texto repete caso da v1, caso da v2 ou exemplo few-shot (checado na geração e na validação, e em `tests/test_validacao_novos_casos.py`).

## Validação
`PYTHONPATH=src python src/validar_dados_v3.py` relê texto, data, valor, moeda, quantidade por extenso, correções e a conta valor total ÷ quantidade com regex independentes do gerador e compara com o gabarito. Resultado: OK nos 20 casos.

## Revisão manual (2026-11-20)
Li os 20 casos, um a um, contra o gabarito (item, área, quantidade e unidade, prazo, valor e moeda, fornecedor). Conferi à mão as seis contas de valor total (100 ÷ 8 = 12,5; 998 ÷ 20 = 49,9; 22,5 ÷ 5 = 4,5; 2.400 ÷ 20 = 120; 1.996 ÷ 40 = 49,9; 3.040 ÷ 8 = 380). Sem divergência.

## Limitações (declarar junto do resultado)
- Só 20 casos e 6 de valor total: o resultado é um indício, não uma garantia.
- O gabarito é do próprio autor do projeto; não há segunda pessoa conferindo.
- Os textos vêm dos mesmos modelos de frase da v2, mais regulares que e-mails reais. Os casos são novos, mas do mesmo estilo.
- A regra de acerto e o critério de "generalizou" foram escritos antes de rodar (`src/comparar_validacao.py`).

## Congelamento
Hashes SHA-256 em `CONGELADO.sha256`. Se `casos_teste.json` ou `gabarito.json` mudar, a validação recusa rodar (`src/rodar.py --validacao`) e este arquivo deve registrar o motivo.
