# Dados v2: método, revisão e limitações

Tudo fictício (empresa fictícia Gutenberg Systems). Prompts e exemplos few-shot são os da v1, sem alteração: só o conjunto de casos mudou.

## Por que existe
A v1 teve 29 respostas erradas, todas por um artefato do gerador (o texto trazia "Ltda." com o ponto de separador de frases e o gabarito não tinha ponto) e os casos ficaram fáceis demais para separar as técnicas. A v2 remove o artefato e acrescenta casos mais difíceis. A v1 continua publicada, com os resultados dela.

## O que mudou em relação à v1
- O gerador nunca coloca ponto depois de "Ltda" (checado por asserção na geração e na validação).
- 27 casos dos 10 tipos da v1 (completa, campos faltando, unidades, valor brasileiro, moeda por símbolo, formatos de data, data relativa, apelido, ruído, duas quantidades) mais 23 casos de 5 tipos novos: correcao (5), valor_total (4), numero_extenso (4), moeda_extenso (4), email_longo (6).
- Nenhum caso v2 repete texto de caso v1 nem exemplo few-shot (checado).

## Regras de rotulagem novas (valem para o gabarito)
- correcao: vale o último valor dito (quantidade, fornecedor ou prazo corrigidos no próprio texto).
- valor_total: `valor_unitario` = valor total / quantidade.
- numero_extenso: quantidade por extenso vira número.
- moeda_extenso: "reais" = BRL, "dólares" = USD, "euros" = EUR; "1.200 euros" = 1200.
- email_longo: só o pedido conta (saudação, assinatura, ramal e aviso são ruído).
- As demais regras da v1 continuam (apelido de fornecedor como aparece; data relativa vira null; etc.).
- Nenhum dos quatro prompts v1 menciona essas regras novas: o modelo precisa inferir. Isso é intencional, mas significa que o gabarito v2 assume uma leitura "de bom senso" que o autor escolheu.

## Validação
`PYTHONPATH=src python src/validar_dados_v2.py` relê texto, data (a última data do texto), valor, moeda, quantidade por extenso e correções com regex independentes do gerador e compara com o gabarito. Resultado em 2026-11-19: OK nos 50 casos. Uma falha apareceu na primeira execução e era do leitor, não do caso ("1.200 euros" lido como 1,2); o leitor foi corrigido antes de qualquer chamada à API.

## Revisão manual (2026-11-19)
Li os 10 casos sorteados com seed 42 (D02, D23, D24, D25, D31, D34, D37, D39, D45, D47) e mais 14 casos dos tipos novos (D28, D29, D30, D32, D33, D35, D36, D38, D40, D41, D42, D43, D44, D50): 24 casos conferidos campo a campo, sem divergência. Os outros 26 foram verificados só pelo script.

## Limitações (declarar no README)
- O gabarito foi criado pelo autor do projeto, não por outra pessoa; não há concordância entre anotadores.
- Textos ainda vêm de modelos de frase, agora com mais variedade, mas mais regulares que e-mails reais.
- As regras novas (valor total, correção, extenso) são decisões do autor sobre o que é "correto".
- Ainda não há medição da v2.

## Congelamento
Hashes SHA-256 em `dados/v2/CONGELADO.sha256`, gravados antes da primeira execução da v2. Se `gabarito.json` ou `casos_teste.json` mudar, registrar aqui e rodar tudo de novo.
