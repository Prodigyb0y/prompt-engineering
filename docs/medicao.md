# Detalhes da medição

Apêndice técnico do [Prompt Lab](../README.md). Aqui ficam intervalo de confiança (bootstrap), teste do sinal pareado, auditoria e a rodada v1. O texto principal evita esse vocabulário de propósito.

## 1. Resumo do que foi medido

- Extração (E1 e E2): 50 casos, 3 repetições, rodadas v1 e v2 e a iteração do T4, **medidas e auditadas** (números abaixo, sem alteração).
- P2 a P5 (E3, E4, E5 e P4): 20 casos por prompt, 3 repetições. Experimentos medidos: 5 de 5 no total (inclui E1 e E2).

## 2. Como cada métrica da extração foi medida

| Métrica | Como foi medida |
|---|---|
| Acerto por caso | JSON válido, schema pydantic válido (`extra="forbid"`) e os 8 campos iguais ao gabarito. Normalização definida antes de medir: texto sem acento, minúsculo e espaços colapsados; números exatos; datas ISO; null só igual a null. Média sobre 3 repetições, com mínimo e máximo entre elas. |
| Acerto por campo e por tipo | Média sobre todas as respostas da técnica. |
| JSON válido | O texto (ou o bloco `<json>` no T3) é um objeto JSON; única tolerância: cerca de markdown ao redor. |
| Custo | Tokens de entrada e saída informados pela API × preço de tabela em `config/precos.json` (US$ 0,10 e US$ 0,50 por 1M de tokens, consultado em 2026-11-19 em https://platform.claude.com/docs/en/about-claude/pricing). Custo por acerto = custo total da técnica / respostas corretas. Tokens de raciocínio contam como saída. |
| Latência | `time.perf_counter` em volta da chamada bem-sucedida; média e mediana. |
| Intervalo de confiança de 95% | Bootstrap percentil, 10.000 reamostragens dos 50 casos, seed 42. |
| Comparação entre técnicas | Só se declara diferença quando os intervalos de 95% não se sobrepõem **e** o teste do sinal exato pareado por caso (bilateral, empates excluídos) dá p < 0,05. O segundo requisito foi acrescentado na auditoria (seção 10): o bootstrap devolve intervalo de largura zero quando a técnica acerta todos os casos. |
| Modelo e execução | `claude-haiku-5-5` (Anthropic, SDK oficial). Cada rodada: 4 técnicas × 50 casos × 3 repetições = 600 respostas; todas com `stop_reason = end_turn` e nenhuma precisou de retry. |

## 3. Resultados da extração (rodadas v2 e v1)

### 3.1 Rodada v2 (principal, `resultados/extracao/v2/RELATORIO.md`)

| Técnica | Prompt | Acerto por caso (média) | IC 95% | Mín–máx entre repetições | JSON válido | Custo por caso (US$) | Custo por acerto (US$) | Latência média / mediana (s) |
|---|---|---|---|---|---|---|---|---|
| T1 zero-shot | v1 `1ef67d6a52fc` | 98.7% | 96.7%–100.0% | 96.0%–100.0% | 100.0% | 0.000125 | 0.000127 | 1.42 / 1.33 |
| T2 few-shot | v1 `be0e8998a563` | 92.7% | 84.7%–98.7% | 92.0%–94.0% | 100.0% | 0.000163 | 0.000176 | 1.31 / 1.10 |
| T3 chain-of-thought | v1 `b3a7a7a94ceb` | 100.0% | 100.0%–100.0% | 100.0%–100.0% | 100.0% | 0.000351 | 0.000351 | 3.29 / 3.21 |
| T4 system prompt | v1 `bb14abcde430` | 92.0% | 84.0%–98.0% | 92.0%–92.0% | 100.0% | 0.000160 | 0.000174 | 1.51 / 1.24 |

- **Nenhuma técnica é declarada melhor.** O T3 acertou 100%, mas só 4 casos o separam de T2 e T4 (4 a favor, 0 contra, p = 0,125 nos dois pares), e contra T1 são 2 casos a favor. Nenhum par chega a p < 0,05 (tabela completa em `resultados/extracao/v2/RELATORIO.md`).
- **Todas as 25 respostas erradas estão no tipo `valor_total`** (4 casos × 3 repetições = 12 respostas por técnica). Nos outros 46 casos as quatro técnicas acertam 100% (recontagem pós-hoc em `resultados/extracao/v2/ERROS.md`).
- **O que aconteceu nesse tipo:** o texto traz só o total ("valor total US$ 350,00" para 10 caixas) e o gabarito exige dividir (35). T3 calculou em 12 de 12; T1 em 10 de 12; T2 devolveu `null` em 11 de 12; T4 devolveu `null` em 12 de 12. Em todos os erros o valor foi `null`; nenhuma resposta devolveu o total como se fosse o unitário.
- **Causa provável:** o T4 diz "se uma informação não estiver no texto, use null" e "não invente valores", e seguiu a própria regra. Os 3 exemplos do T2 trazem sempre o preço unitário explícito, e ele provavelmente repetiu esse padrão (hipótese, não testada). Com outro gabarito ("deixe null quando só há o total"), o ranking nesse tipo se inverteria.
- **Consequência:** a vantagem numérica do T3 vem de 4 casos de um único tipo e de uma regra de rotulagem minha que os prompts não mencionam. É um resultado sobre **como cada prompt trata um dado implícito**, não uma medida geral de qualidade.
- **Custo e tempo:** custo por caso T1 US$ 0,000125, T2 US$ 0,000163, T3 US$ 0,000351, T4 US$ 0,000160; o T3 custou 2,8 vezes o T1 e levou 2,3 vezes mais tempo.

### 3.2 Iteração de prompt: T4 v1 → v2 (`resultados/extracao/v2/ITERACAO.md`)

O T4 v1 errou 12 de 12 respostas do tipo `valor_total`. O T4 v2 (hash `2c3ccc1873da`) muda o prompt em duas linhas: acrescenta "se só houver o valor total, divida pela quantidade" e ajusta a regra de moeda. Foi rodado só o T4 v2, nos mesmos 50 casos v2, com 3 repetições (150 chamadas).

| | T4 v1 | T4 v2 |
|---|---|---|
| Acerto por caso (média de 3 repetições) | 92,0% | 100,0% |
| Tipo `valor_total`: respostas certas | 0 de 12 | 12 de 12 |
| Outros 14 tipos: respostas certas | todas | todas |
| Custo por resposta (US$) | 0,000160 | 0,000145 |
| Tokens de saída médios | 177 | 133 |

- **Sem regressão:** nenhum caso piorou; 4 casos melhoraram.
- **Estatística:** p = 0,125 no teste do sinal exato pareado; com tão poucos casos discordantes o teste não chega a p < 0,05 mesmo com todos na mesma direção. A causa da queda de tokens de saída não foi investigada.
- **Limite:** a regra do T4 v2 foi escrita depois de ver os erros nesses mesmos 50 casos. É um resultado de desenvolvimento: mostra o ciclo medir → diagnosticar → corrigir → medir de novo, sem regressão, mas não prova que a regra vale para casos novos. O T3 não foi ajustado e o T4 v2 foi, então a comparação entre os dois não é simétrica (o T3 custou US$ 0,000351 por caso na v2).
- **Verificação:** a reavaliação das 150 respostas brutas com o validador deu 0 divergências; o custo recalculado bate com o livro-caixa.

### 3.3 Rodada v1 (histórica, `resultados/extracao/v1/RELATORIO.md`)

| Técnica | Prompt | Acerto por caso (média) | IC 95% | Mín–máx entre repetições | JSON válido | Custo por caso (US$) | Custo por acerto (US$) | Latência média / mediana (s) |
|---|---|---|---|---|---|---|---|---|
| T1 zero-shot | v1 `1ef67d6a52fc` | 95.3% | 89.3%–100.0% | 94.0%–96.0% | 100.0% | 0.000108 | 0.000114 | 1.32 / 1.21 |
| T2 few-shot | v1 `be0e8998a563` | 98.0% | 94.0%–100.0% | 98.0%–98.0% | 100.0% | 0.000143 | 0.000146 | 1.14 / 0.97 |
| T3 chain-of-thought | v1 `b3a7a7a94ceb` | 97.3% | 92.7%–100.0% | 96.0%–98.0% | 100.0% | 0.000330 | 0.000339 | 3.17 / 3.06 |
| T4 system prompt | v1 `bb14abcde430` | 90.0% | 82.0%–98.0% | 90.0%–90.0% | 100.0% | 0.000126 | 0.000140 | 1.20 / 1.02 |

As 29 respostas erradas têm a mesma causa: o texto de cinco casos traz "Papelaria Aurora Ltda." com um ponto de separador de frase que o meu gerador inseriu, e o gabarito não tem ponto. Os modelos copiaram a abreviação como estava escrita. É **artefato do caso, não erro de modelo**. Na recontagem pós-hoc (não oficial) as quatro técnicas chegam a 100% (`resultados/extracao/v1/ERROS.md`). Mantive o resultado oficial, porque mudar a regra depois de ver o resultado quebraria o congelamento. Conclusão da v1: acerto entre 90,0% e 98,0%, intervalos que se sobrepõem, **nenhuma técnica declarada melhor**; a tarefa ficou fácil demais, e por isso criei a v2.

## 4. Rodadas novas: P2 a P5 (E3, E4, E5 e P4)

Regras de acerto, escritas antes de qualquer rodada paga (código em `src/avaliadores.py`):

```text
Cada avaliador recebe (resposta, gabarito, ...) e devolve:
  {"json_valido": bool, "campos": {nome: bool}, "caso_correto": bool, ...extras}

P2  acerto = JSON válido, com as duas chaves e nenhuma a mais, e categoria e urgência iguais ao gabarito.
P3  acerto = o e-mail cita todos os campos que faltam e nenhum que não falta (nome exato do campo, sem acento e
    sem diferença de maiúsculas); se nada falta, a resposta é exatamente NENHUM_CAMPO_FALTANTE. Tom e qualidade
    do texto NÃO entram no acerto (só o formato e o tamanho, como informação à parte).
P4  acerto = JSON válido com as 6 chaves, enums válidos, motivo, sentimento, ação, número do pedido e valor iguais
    ao gabarito (null só igual a null) e resumo de até 20 palavras sem número que não esteja no texto da reclamação.
    "Invenção" = número do pedido ou valor preenchido quando o gabarito é null (contada à parte).
P5  acerto = decisão igual ao gabarito. Com chain-of-thought só o bloco <json> é lido; o raciocínio é ignorado.
```

Escala: 20 casos por prompt novo, 3 repetições por variante, piloto de 5 chamadas por prompt antes da rodada completa. Teto das rodadas novas: US$ 0,60 (e nunca mais que US$ 1,00 no total do repositório, contando o gasto anterior de US$ 0,248969). Intervalo de confiança: bootstrap percentil, 10.000 reamostragens dos 20 casos, seed 42. Comparação: teste do sinal exato pareado por caso, empates excluídos; com 20 casos, p < 0,05 é raro.

Dados: [`dados/biblioteca/REVISAO_E_LIMITACOES.md`](../dados/biblioteca/REVISAO_E_LIMITACOES.md) (revisão manual, correções do gabarito do P4 e limitações). Gabaritos congelados por hash em `dados/biblioteca/<p2..p5>/CONGELADO.sha256`.

| Exp. | Variante | Acerto | IC 95% | Mín–máx entre repetições | Custo por resposta | Respostas | Completa |
|---|---|---|---|---|---|---|---|
| E3 | Zero-shot | 91,7% | 78,3%–100,0% | 90,0%–95,0% | US$ 0,000073 | 60 | sim |
| E3 | Few-shot | 98,3% | 95,0%–100,0% | 95,0%–100,0% | US$ 0,000137 | 60 | sim |
| E4 | Encadeado (P1 → P3) | 78,3% | 65,0%–90,0% | 75,0%–80,0% | US$ 0,000256 | 60 | sim |
| E4 | Prompt único (extrai e escreve) | 81,7% | 65,0%–96,7% | 75,0%–85,0% | US$ 0,000270 | 60 | sim |
| P4 | Saída estruturada | 95,0% | 86,7%–100,0% | 90,0%–100,0% | US$ 0,000219 | 60 | sim |
| E5 | Sem raciocínio | 95,0% | 85,0%–100,0% | 95,0%–95,0% | US$ 0,000123 | 60 | sim |
| E5 | Com raciocínio (chain-of-thought) | 100,0% | 100,0%–100,0% | 100,0%–100,0% | US$ 0,000278 | 60 | sim |

Comparações pareadas:

| Exp. | Par (base contra alternativa) | Casos a favor da base | Casos a favor da alternativa | p (sinal exato) |
|---|---|---|---|---|
| E3 | Zero-shot contra Few-shot | 1 | 2 | 1,000 |
| E4 | Prompt único (extrai e escreve) contra Encadeado (P1 → P3) | 6 | 4 | 0,754 |
| E5 | Sem raciocínio contra Com raciocínio (chain-of-thought) | 0 | 1 | 1,000 |

Custo das rodadas novas: US$ 0,085039 em 500 chamadas (piloto US$ 0,003544, rodadas US$ 0,081495). Relatório completo: `resultados/biblioteca/RELATORIO.md` (gerado por `src/analisar_biblioteca.py`).

## 5. Auditoria e decisões registradas

`python src/auditar.py` recalcula acerto e custo direto das respostas brutas, reaplica o validador a todas as respostas e mede a diversidade dos dados. Nas duas rodadas: 0 divergências entre a avaliação gravada e a recalculada, e acerto e custo iguais aos do resumo.

- **Sem temperatura 0 (2026-11-19).** O `claude-haiku-5-5` não aceita `temperature`, `top_p` nem `top_k`; a primeira tentativa de piloto falhou no SDK antes de qualquer chamada paga (custo zero).
- **Raciocínio adaptativo ligado por padrão.** Fixei `effort = "low"` para limitar o raciocínio oculto e o custo; fica registrado em cada resultado bruto.
- **Artefato do "Ltda."**, descoberto depois da rodada v1: resultado oficial mantido, recontagem pós-hoc separada, dados v2 gerados sem o artefato.
- **Tipo `valor_total` da v2**, que concentrou todos os erros: resultado oficial mantido, causa e recontagem sem o tipo documentadas.
- **Correção do critério de vencedor (2026-11-20).** A primeira versão do relatório dizia que, na v2, o T3 ficava acima de T2 e T4 porque os intervalos de 95% não se sobrepunham. Era um artefato: o intervalo do T3 é 100%–100% (largura zero). Com o teste do sinal exato pareado, p = 0,125 nos dois pares. O critério passou a exigir os dois requisitos e a declaração foi retirada; na v1 nenhuma declaração mudou.
- **Iteração do T4 (2026-11-20):** executada e verificada (7.2).

## 6. Dados da extração

A partir de uma mensagem livre de solicitação de compra, extrair um JSON com 8 campos: `solicitante_area`, `item`, `quantidade`, `unidade` (`un`, `kg`, `m`, `l`, `cx`), `prazo_entrega` (AAAA-MM-DD ou null), `valor_unitario`, `moeda` (`BRL`, `USD`, `EUR` ou null) e `fornecedor`.

| Conjunto | Pasta | Casos | Observação |
|---|---|---|---|
| Rodada v1 | `dados/` | 50 casos em 10 tipos | completa, campos faltando, unidades, valor brasileiro, moeda por símbolo, formatos de data, data relativa, apelido de fornecedor, ruído, duas quantidades |
| Rodada v2 | `dados/extracao/v2/` | 50 casos novos em 15 tipos | 27 casos dos 10 tipos antigos e 23 de 5 tipos mais difíceis (correção no meio do texto, valor total, quantidade por extenso, moeda por extenso, e-mail longo); sem o artefato do "Ltda." da v1 |

- O gabarito é gerado por script (seed 42) a partir de um registro estruturado e **congelado antes da primeira execução** de cada rodada (hashes em `dados/CONGELADO.sha256` e `dados/extracao/v2/CONGELADO.sha256`, conferidos por teste).
- **A v2 foi criada depois de ver os resultados da v1.** Está dito aqui para não parecer o contrário.
- Os mesmos 3 exemplos few-shot (`dados/exemplos_fewshot.json`) nas duas rodadas; nenhum repete um caso de teste.
- Validação: um script relê o texto de forma independente do gerador e compara com o gabarito. Revisão manual: 10 casos da v1 e 24 da v2. Detalhes em `dados/extracao/v1/REVISAO_E_LIMITACOES.md` e `dados/extracao/v2/REVISAO_E_LIMITACOES.md`.

## 7. Mapa de caminhos (reorganização do repositório)

O repositório foi reorganizado em "biblioteca + experimentos". Os arquivos de resultado antigos foram **movidos sem alteração de conteúdo** (os hashes de congelamento continuam batendo, e há teste para isso); por isso os relatórios gerados originalmente ainda citam os caminhos antigos no próprio texto.

| Antes | Agora |
|---|---|
| `dados/*.json` | `dados/extracao/v1/` |
| `dados/extracao/v2/` | `dados/extracao/v2/` |
| `resultados/*.md`, `resumo.json` | `resultados/extracao/v1/` |
| `resultados/v2/` | `resultados/extracao/v2/` |
| `prompts/T*.json` | `prompts/extracao/` |
| `docs/index.html` (demo anterior) | substituída; o código antigo está em `src/legado/` |

As respostas brutas da rodada v2 ficavam fora do Git; as respostas gravadas que a demo anterior embutia foram preservadas em `resultados/extracao/v2/respostas_gravadas.json` (recalculam exatamente o acerto oficial, e há teste para isso). As respostas brutas da iteração T4 v2 não foram preservadas: só os totais (`iteracao.json`).

### Comandos das rodadas antigas (extração)

```bash
PE_VERSAO=v2 .venv/bin/python src/rodar.py --completo    # PowerShell: $env:PE_VERSAO="v2"
PE_VERSAO=v2 .venv/bin/python src/rodar.py --iteracao
.venv/bin/python src/analisar.py ; .venv/bin/python src/auditar.py ; .venv/bin/python src/classificar_erros.py
```

O README anterior (estudo de avaliação) está preservado em [`docs/legado/README_estudo_de_avaliacao.md`](legado/README_estudo_de_avaliacao.md).
