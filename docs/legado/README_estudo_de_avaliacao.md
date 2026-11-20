# Laboratório de prompt engineering

**Mesma tarefa, mesmos casos, quatro técnicas de prompt: o que acerta mais, e quanto custa cada acerto.**

Projeto de portfólio com exemplos de prompts bem estruturados e experimentações com LLMs. É uma recriação conceitual com **dados 100% fictícios** (empresa fictícia Gutenberg Systems); não há dados, nomes, sistemas ou documentos de nenhuma empresa real.

**Conteúdo:** [1. Resumo](#1-resumo) · [2. Demo](#2-demo) · [3. Problema e usuário](#3-problema-e-usuário) · [4. Tarefa e dados](#4-tarefa-e-dados) · [5. Técnicas](#5-técnicas-de-prompt) · [6. Métricas](#6-como-cada-métrica-foi-medida) · [7. Resultados](#7-resultados) · [8. Para um time de negócio](#8-o-que-isso-significa-para-um-time-de-negócio) · [9. Limitações](#9-limitações) · [10. Auditoria e decisões](#10-auditoria-e-decisões-registradas) · [11. Como rodar](#11-como-rodar) · [12. Estrutura](#12-estrutura-do-repositório) · [13. Próximos passos](#13-próximos-passos)

## 1. Resumo

Pedi ao mesmo modelo (`claude-haiku-5-5`) para ler pedidos de compra escritos em texto livre ("preciso de 10 caixas de papel A4, entrega até dia 15...") e devolver os dados em 8 campos. Comparei **quatro jeitos de pedir**: só a instrução (zero-shot), a instrução com exemplos (few-shot), raciocínio passo a passo antes da resposta (chain-of-thought) e papel e regras num system prompt. Escrevi o gabarito **antes** de rodar, para não ajustar o teste ao resultado.

Principais achados:

1. **Em pedidos simples, qualquer técnica funciona.** Na rodada v2, nos 46 dos 50 casos que não envolvem cálculo, as quatro técnicas acertaram 100%.
2. **A diferença apareceu em um único tipo de caso**: o texto traz só o *valor total* e o campo pedido é o *valor unitário*. O T3 calculou certo em 12 de 12 respostas, o T1 em 10 de 12, o T2 em 1 de 12 e o T4 em 0 de 12. São só 4 casos e o teste pareado não sustenta que uma técnica seja melhor (p = 0,125): é um indício, não uma conclusão.
3. **A regra de negócio precisa estar escrita no prompt.** O T4 tinha a regra "se a informação não está no texto, use null" e obedeceu. Calcular ou deixar vazio é uma decisão que eu tomei no gabarito e que nenhum prompt dizia.
4. **Medir, diagnosticar, corrigir e medir de novo funcionou, com ressalva.** Acrescentei ao T4 uma regra para o valor total (T4 v2): o acerto foi de 92,0% para 100,0% sem regressão nos outros tipos. A regra foi escrita olhando os mesmos casos em que foi medida, então é resultado de desenvolvimento, não prova de generalização.
5. **Raciocinar passo a passo custou mais**: cerca de 2,8 vezes o custo por caso e 2,3 vezes o tempo do zero-shot na rodada v2.
6. **Parte do meu próprio teste estava errada** na primeira rodada (um ponto final depois de "Ltda"). Descobri, documentei e refiz os dados em vez de esconder.

## 2. Demo

**https://prodigyb0y.github.io/prompt-engineering/** (sem instalação e sem chave; GitHub Pages servindo `docs/`). O arquivo [`docs/index.html`](docs/index.html) também abre direto no navegador.

A página mostra o resumo por técnica, a metodologia (incluindo a anatomia do system prompt), os resultados com intervalo de confiança, a análise de erros, a iteração do prompt e um explorador dos 50 casos (texto, gabarito e saída de cada técnica, por repetição). Todos os números vêm dos arquivos de resultado; nada é digitado à mão.

## 3. Problema e usuário

Times de negócio gastam tempo corrigindo à mão dados extraídos de textos livres (pedidos de compra, e-mails). Escolher a técnica de prompt por intuição sai caro e ninguém sabe se valeu a pena. **Quem usa:** um time de compras (ou operações) que recebe solicitações em texto livre e precisa delas em campos.

## 4. Tarefa e dados

A partir de uma mensagem livre de solicitação de compra, extrair um JSON com 8 campos: `solicitante_area`, `item`, `quantidade`, `unidade` (`un`, `kg`, `m`, `l`, `cx`), `prazo_entrega` (AAAA-MM-DD ou null), `valor_unitario`, `moeda` (`BRL`, `USD`, `EUR` ou null) e `fornecedor`.

| Conjunto | Pasta | Casos | Observação |
|---|---|---|---|
| Rodada v1 | `dados/` | 50 casos em 10 tipos | completa, campos faltando, unidades, valor brasileiro, moeda por símbolo, formatos de data, data relativa, apelido de fornecedor, ruído, duas quantidades |
| Rodada v2 | `dados/v2/` | 50 casos novos em 15 tipos | 27 casos dos 10 tipos antigos e 23 de 5 tipos mais difíceis (correção no meio do texto, valor total, quantidade por extenso, moeda por extenso, e-mail longo); sem o artefato do "Ltda." da v1 |

- O gabarito é gerado por script (seed 42) a partir de um registro estruturado e **congelado antes da primeira execução** de cada rodada (hashes em `dados/CONGELADO.sha256` e `dados/v2/CONGELADO.sha256`, conferidos por teste).
- **A v2 foi criada depois de ver os resultados da v1.** Está dito aqui para não parecer o contrário.
- Os mesmos 3 exemplos few-shot (`dados/exemplos_fewshot.json`) nas duas rodadas; nenhum repete um caso de teste.
- Validação: um script relê o texto de forma independente do gerador e compara com o gabarito. Revisão manual: 10 casos da v1 e 24 da v2. Detalhes em `dados/REVISAO_E_LIMITACOES.md` e `dados/v2/REVISAO_E_LIMITACOES.md`.

## 5. Técnicas de prompt

| Id | Técnica | O que muda no prompt |
|---|---|---|
| T1 | zero-shot | instrução e schema, sem exemplos |
| T2 | few-shot | instrução, schema e 3 exemplos fixos |
| T3 | chain-of-thought | raciocínio em `<raciocinio>` e JSON em `<json>`; só o `<json>` é lido |
| T4 | system prompt | papel, regras e formato no system prompt, sem exemplos |

Os prompts estão em `prompts/` (JSON com versão e SHA-256 de 12 caracteres), são iguais para todos os casos e **idênticos nas duas rodadas** (testado: os hashes não mudam). Hashes v1: T1 `1ef67d6a52fc`, T2 `be0e8998a563`, T3 `b3a7a7a94ceb`, T4 `bb14abcde430`. Existe uma segunda versão só do T4 (`prompts/T4_system_prompt_v2.json`, `2c3ccc1873da`), criada depois de ver resultados, na iteração descrita em 7.2. Nenhum prompt foi alterado sem criar nova versão.

## 6. Como cada métrica foi medida

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

## 7. Resultados

### 7.1 Rodada v2 (principal, `resultados/v2/RELATORIO.md`)

| Técnica | Prompt | Acerto por caso (média) | IC 95% | Mín–máx entre repetições | JSON válido | Custo por caso (US$) | Custo por acerto (US$) | Latência média / mediana (s) |
|---|---|---|---|---|---|---|---|---|
| T1 zero-shot | v1 `1ef67d6a52fc` | 98.7% | 96.7%–100.0% | 96.0%–100.0% | 100.0% | 0.000125 | 0.000127 | 1.42 / 1.33 |
| T2 few-shot | v1 `be0e8998a563` | 92.7% | 84.7%–98.7% | 92.0%–94.0% | 100.0% | 0.000163 | 0.000176 | 1.31 / 1.10 |
| T3 chain-of-thought | v1 `b3a7a7a94ceb` | 100.0% | 100.0%–100.0% | 100.0%–100.0% | 100.0% | 0.000351 | 0.000351 | 3.29 / 3.21 |
| T4 system prompt | v1 `bb14abcde430` | 92.0% | 84.0%–98.0% | 92.0%–92.0% | 100.0% | 0.000160 | 0.000174 | 1.51 / 1.24 |

- **Nenhuma técnica é declarada melhor.** O T3 acertou 100%, mas só 4 casos o separam de T2 e T4 (4 a favor, 0 contra, p = 0,125 nos dois pares), e contra T1 são 2 casos a favor. Nenhum par chega a p < 0,05 (tabela completa em `resultados/v2/RELATORIO.md`).
- **Todas as 25 respostas erradas estão no tipo `valor_total`** (4 casos × 3 repetições = 12 respostas por técnica). Nos outros 46 casos as quatro técnicas acertam 100% (recontagem pós-hoc em `resultados/v2/ERROS.md`).
- **O que aconteceu nesse tipo:** o texto traz só o total ("valor total US$ 350,00" para 10 caixas) e o gabarito exige dividir (35). T3 calculou em 12 de 12; T1 em 10 de 12; T2 devolveu `null` em 11 de 12; T4 devolveu `null` em 12 de 12. Em todos os erros o valor foi `null`; nenhuma resposta devolveu o total como se fosse o unitário.
- **Causa provável:** o T4 diz "se uma informação não estiver no texto, use null" e "não invente valores", e seguiu a própria regra. Os 3 exemplos do T2 trazem sempre o preço unitário explícito, e ele provavelmente repetiu esse padrão (hipótese, não testada). Com outro gabarito ("deixe null quando só há o total"), o ranking nesse tipo se inverteria.
- **Consequência:** a vantagem numérica do T3 vem de 4 casos de um único tipo e de uma regra de rotulagem minha que os prompts não mencionam. É um resultado sobre **como cada prompt trata um dado implícito**, não uma medida geral de qualidade.
- **Custo e tempo:** custo por caso T1 US$ 0,000125, T2 US$ 0,000163, T3 US$ 0,000351, T4 US$ 0,000160; o T3 custou 2,8 vezes o T1 e levou 2,3 vezes mais tempo.

### 7.2 Iteração de prompt: T4 v1 → v2 (`resultados/v2/ITERACAO.md`)

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

### 7.3 Rodada v1 (histórica, `resultados/RELATORIO.md`)

| Técnica | Prompt | Acerto por caso (média) | IC 95% | Mín–máx entre repetições | JSON válido | Custo por caso (US$) | Custo por acerto (US$) | Latência média / mediana (s) |
|---|---|---|---|---|---|---|---|---|
| T1 zero-shot | v1 `1ef67d6a52fc` | 95.3% | 89.3%–100.0% | 94.0%–96.0% | 100.0% | 0.000108 | 0.000114 | 1.32 / 1.21 |
| T2 few-shot | v1 `be0e8998a563` | 98.0% | 94.0%–100.0% | 98.0%–98.0% | 100.0% | 0.000143 | 0.000146 | 1.14 / 0.97 |
| T3 chain-of-thought | v1 `b3a7a7a94ceb` | 97.3% | 92.7%–100.0% | 96.0%–98.0% | 100.0% | 0.000330 | 0.000339 | 3.17 / 3.06 |
| T4 system prompt | v1 `bb14abcde430` | 90.0% | 82.0%–98.0% | 90.0%–90.0% | 100.0% | 0.000126 | 0.000140 | 1.20 / 1.02 |

As 29 respostas erradas têm a mesma causa: o texto de cinco casos traz "Papelaria Aurora Ltda." com um ponto de separador de frase que o meu gerador inseriu, e o gabarito não tem ponto. Os modelos copiaram a abreviação como estava escrita. É **artefato do caso, não erro de modelo**. Na recontagem pós-hoc (não oficial) as quatro técnicas chegam a 100% (`resultados/ERROS.md`). Mantive o resultado oficial, porque mudar a regra depois de ver o resultado quebraria o congelamento. Conclusão da v1: acerto entre 90,0% e 98,0%, intervalos que se sobrepõem, **nenhuma técnica declarada melhor**; a tarefa ficou fácil demais, e por isso criei a v2.

### 7.4 Custo gasto

**US$ 0,248969 de um teto de US$ 1,00.** Detalhe conforme o livro-caixa do cliente: v1 (piloto de 10 chamadas mais 600) US$ 0,107289; v2 (600 chamadas) US$ 0,119941; iteração do T4 (150 chamadas) US$ 0,021739. O cliente reserva o custo máximo antes de cada chamada e para com erro registrado se a próxima passaria do teto (testado em `tests/test_custo_e_cliente.py`).

## 8. O que isso significa para um time de negócio

- Para extrair dados de texto livre, um modelo pequeno acertou ao menos 90,0% dos casos com qualquer técnica, nas duas rodadas, e 100% dos 46 casos da v2 que não envolvem cálculo.
- **A regra de negócio vale mais que a técnica.** O que separou as técnicas foi uma pergunta que a empresa precisa responder e escrever no prompt (quando só há o total, calcular ou deixar vazio?).
- Pagar por raciocínio passo a passo custou cerca de 3 vezes mais por caso (2,8 na v2 e 3,0 na v1); só mostrou vantagem numérica, sem significância estatística, onde havia cálculo implícito.
- Antes de escolher a técnica mais cara, vale medir com casos do seu próprio problema. Vale para esta tarefa e este modelo; não é regra geral.

## 9. Limitações

- **Só 50 casos por rodada** (duas rodadas, v1 e v2), de textos gerados por modelos de frase, mais regulares que e-mails reais. Na v2, a diferença entre técnicas vem de 4 casos de um único tipo.
- **Um modelo só** (`claude-haiku-5-5`); não comparei provedores.
- **O gabarito foi criado pelo autor do projeto, não por outra pessoa**; não há concordância entre anotadores. Na v2 as regras novas (como calcular o valor unitário a partir do total) são decisões do autor e decidem o resultado do único tipo em que houve diferença.
- **A v2 foi desenhada depois de ver a v1**, para corrigir o artefato e dificultar a tarefa; não é uma segunda medição independente.
- **A regra do T4 v2 foi escrita depois de ver os erros nos mesmos 50 casos** em que foi medida; os 100,0% são resultado de desenvolvimento, não prova de generalização.
- **Sem temperatura 0:** o modelo não aceita `temperature`. A variação foi medida por 3 repetições, que não provam determinismo.
- **Raciocínio do modelo:** o raciocínio adaptativo vem ligado por padrão; fixei `effort = "low"`. Todas as técnicas podem raciocinar internamente, o que dilui a diferença da chain-of-thought.
- **Baixo poder de discriminação e pouca variedade:** só 5 (v1) e 4 (v2) dos 50 casos têm alguma resposta errada; há 17 itens distintos em cada rodada e parte dos casos usa o mesmo item ou fornecedor de algum exemplo do T2 (contagens em `resultados/AUDITORIA.md` e `resultados/v2/AUDITORIA.md`).
- Resultados não generalizáveis para outras tarefas, idiomas ou modelos.

## 10. Auditoria e decisões registradas

`python src/auditar.py` recalcula acerto e custo direto das respostas brutas, reaplica o validador a todas as respostas e mede a diversidade dos dados. Nas duas rodadas: 0 divergências entre a avaliação gravada e a recalculada, e acerto e custo iguais aos do resumo.

- **Sem temperatura 0 (2026-11-19).** O `claude-haiku-5-5` não aceita `temperature`, `top_p` nem `top_k`; a primeira tentativa de piloto falhou no SDK antes de qualquer chamada paga (custo zero).
- **Raciocínio adaptativo ligado por padrão.** Fixei `effort = "low"` para limitar o raciocínio oculto e o custo; fica registrado em cada resultado bruto.
- **Artefato do "Ltda."**, descoberto depois da rodada v1: resultado oficial mantido, recontagem pós-hoc separada, dados v2 gerados sem o artefato.
- **Tipo `valor_total` da v2**, que concentrou todos os erros: resultado oficial mantido, causa e recontagem sem o tipo documentadas.
- **Correção do critério de vencedor (2026-11-20).** A primeira versão do relatório dizia que, na v2, o T3 ficava acima de T2 e T4 porque os intervalos de 95% não se sobrepunham. Era um artefato: o intervalo do T3 é 100%–100% (largura zero). Com o teste do sinal exato pareado, p = 0,125 nos dois pares. O critério passou a exigir os dois requisitos e a declaração foi retirada; na v1 nenhuma declaração mudou.
- **Iteração do T4 (2026-11-20):** executada e verificada (7.2).

## 11. Como rodar

```bash
git clone https://github.com/Prodigyb0y/prompt-engineering
cd prompt-engineering
python -m venv .venv && .venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\python.exe -m pip ...
.venv/bin/python -m pytest -q                       # testes que não chamam API
cp .env.example .env                                # preencha ANTHROPIC_API_KEY (nunca versione o .env)
.venv/bin/python src/rodar.py --piloto              # 10 chamadas
.venv/bin/python src/rodar.py --completo            # rodada v1: 600 chamadas, retomável
PE_VERSAO=v2 .venv/bin/python src/rodar.py --completo   # rodada v2 (PowerShell: $env:PE_VERSAO="v2")
PE_VERSAO=v2 .venv/bin/python src/rodar.py --iteracao   # T4 v2, 150 chamadas
.venv/bin/python src/analisar.py                    # RELATORIO.md e resumo.json (com PE_VERSAO=v2: resultados/v2/)
.venv/bin/python src/classificar_erros.py           # ERROS.md
.venv/bin/python src/auditar.py                     # AUDITORIA.md
PE_VERSAO=v2 .venv/bin/python src/comparar_iteracao.py   # resultados/v2/ITERACAO.md
.venv/bin/python src/gerar_demo.py                  # docs/index.html (usa os resultados v2)
```

Os resultados brutos (`resultados/brutos/`, `resultados/v2/brutos/`, `resultados/v2/iteracao/brutos/`) não vão para o Git. Quem refizer as rodadas pode obter números diferentes, porque o modelo não aceita temperatura 0.

## 12. Estrutura do repositório

```
dados/            rodada v1: casos, gabarito, exemplos few-shot, hashes (fictícios)
dados/v2/         rodada v2: casos, gabarito, hashes
prompts/          T1 a T4 (v1) e T4 v2, com versão e hash
config/           precos.json (preço de tabela, data e fonte)
src/              geradores de dados, validador, cliente com teto de gasto, custo, execução, análise, auditoria, demo
tests/            testes que não chamam a API
resultados/       relatórios da rodada v1 (RELATORIO, ERROS, AUDITORIA, resumo.json)
resultados/v2/    relatórios da rodada v2 e da iteração (ITERACAO.md, iteracao.json)
docs/             index.html (demo) e checklist_entrega.md
```

## 13. Próximos passos

**Não feito nesta entrega (fora do escopo, registrado):**

- Validar o T4 v2 em casos novos, escritos e congelados antes de rodar, porque a regra foi escrita olhando os 50 casos v2.
- Segunda pessoa para rotular o gabarito e medir concordância.

**Ideias futuras:** a mesma iteração no T2 com um exemplo em que o total vira valor unitário (regra escrita contra exemplo); ablação do system prompt (T1 com as regras do T4 na mensagem do usuário); mais casos por tipo (hoje 4 de `valor_total`); comparar com outro modelo, se houver orçamento.
