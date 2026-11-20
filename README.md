# Laboratório de prompt engineering

**Mesma tarefa, mesmos casos, quatro técnicas de prompt: o que acerta mais, e quanto custa cada acerto.**

Projeto de portfólio. É uma recriação conceitual com **dados 100% fictícios** (empresa fictícia Gutenberg Systems). Não há dados, nomes, sistemas ou documentos de nenhuma empresa real.

## Em linguagem simples

Pedi à mesma IA para ler pedidos de compra escritos em texto livre ("preciso de 10 caixas de papel A4, entrega até dia 15...") e devolver os dados em campos organizados. Testei **quatro jeitos de fazer o pedido à IA**: só a instrução (zero-shot), a instrução com exemplos (few-shot), pedindo para raciocinar passo a passo (chain-of-thought) e dando um papel e regras fixas (system prompt). Escrevi as respostas certas **antes** de rodar, para não ajustar o teste ao resultado.

O que descobri:

1. **Em pedidos simples, qualquer jeito funciona.** Em 46 dos 50 casos da segunda rodada as quatro técnicas acertaram 100%.
2. **A diferença apareceu em um único tipo de caso:** quando o texto traz só o *valor total* e a pergunta é o *valor de cada unidade*. Raciocinar passo a passo (T3) calculou certo em todas as vezes; a instrução simples (T1) calculou na maior parte; o jeito com exemplos (T2) e o com regras (T4) deixaram o campo vazio.
3. **Isso não é só "quem entende melhor".** O T4 tinha a regra "se a informação não está no texto, deixe em branco", e obedeceu. Foi uma decisão de negócio (calcular ou deixar vazio?) que eu tomei no gabarito e que nenhum prompt dizia. Lição prática: **a regra de negócio precisa estar escrita no prompt**, e o "melhor" depende do que a empresa quer.
4. **Raciocinar passo a passo custou mais:** na segunda rodada, cerca de 2,8 vezes o custo por caso e 2,3 vezes o tempo da instrução simples.
5. **Parte do meu próprio teste estava errada** (na primeira rodada, um ponto final depois de "Ltda"). Descobri, expliquei, e refiz os dados em vez de esconder.

## O problema e para quem

Times de negócio gastam tempo corrigindo à mão dados extraídos de textos livres (pedidos de compra, e-mails). Escolher a técnica de prompt por intuição sai caro, e ninguém sabe se valeu a pena. **Quem usa:** um time de compras (ou operações) que recebe solicitações em texto livre e precisa delas em campos.

## Demo (sem instalação, sem chave)

- Rodada v1: **https://prodigyb0y.github.io/prompt-engineering/** (carregamento confirmado pelo autor em 2026-11-19).
- Rodada v2: **https://prodigyb0y.github.io/prompt-engineering/v2/** (publicada junto, na mesma pasta `docs/`; a abertura deste endereço ainda não foi verificada).

Cada página tem a tabela por técnica e um explorador dos 50 casos (texto, gabarito e saída de cada técnica, por repetição). Também abrem direto dos arquivos [`docs/index.html`](docs/index.html) e [`docs/v2/index.html`](docs/v2/index.html).

## A tarefa e os dados (fictícios)

A partir de uma mensagem livre de solicitação de compra, extrair um JSON com 8 campos: `solicitante_area`, `item`, `quantidade`, `unidade` (`un`, `kg`, `m`, `l`, `cx`), `prazo_entrega` (AAAA-MM-DD ou null), `valor_unitario`, `moeda` (`BRL`, `USD`, `EUR` ou null) e `fornecedor`.

- **Dados v1** (`dados/`): 50 casos em 10 tipos (completa, campos faltando, unidades, valor brasileiro, moeda por símbolo, formatos de data, data relativa, apelido de fornecedor, ruído, duas quantidades).
- **Dados v2** (`dados/v2/`): 50 casos novos, sem o artefato do "Ltda." da v1, com 27 casos dos 10 tipos antigos e 23 de 5 tipos mais difíceis: correção no meio do texto, valor total, quantidade por extenso, moeda por extenso e e-mail longo. **A v2 foi criada depois de ver os resultados da v1**; está dito aqui para não parecer o contrário.
- Gabarito gerado por script (seed 42) a partir de registro estruturado e **congelado antes da primeira execução** de cada versão (hashes em `dados/CONGELADO.sha256` e `dados/v2/CONGELADO.sha256`, conferidos por teste).
- Os mesmos 3 exemplos few-shot nas duas rodadas; nenhum repete um caso de teste.
- Validação: script que relê o texto de forma independente do gerador e compara com o gabarito. Revisão manual: 10 casos da v1; 24 casos da v2 (os 10 sorteados e mais 14 dos tipos novos). Detalhes em `dados/REVISAO_E_LIMITACOES.md` e `dados/v2/REVISAO_E_LIMITACOES.md`.

## As quatro técnicas (v1, cada uma com hash do texto)

| Id | Técnica | O que muda |
|---|---|---|
| T1 | zero-shot | instrução e schema, sem exemplos |
| T2 | few-shot | instrução, schema e 3 exemplos fixos |
| T3 | chain-of-thought | raciocínio em `<raciocinio>` e JSON em `<json>`; só o `<json>` é lido |
| T4 | system prompt | papel, regras e formato no system prompt, sem exemplos |

Os prompts estão em `prompts/` (JSON com versão e SHA-256 de 12 caracteres), são iguais para todos os casos e **são os mesmos nas duas rodadas** (testado: os hashes não mudam). Nenhum prompt foi alterado depois de ver resultado.

## Como cada métrica foi medida

- **Acerto por caso:** JSON válido, schema pydantic válido (`extra="forbid"`) e os 8 campos iguais ao gabarito. Normalização definida antes de medir: texto sem acento, minúsculo e espaços colapsados; números exatos; datas ISO; null só igual a null. Média sobre 3 repetições, com mínimo e máximo entre as repetições.
- **Acerto por campo e por tipo:** média sobre todas as respostas da técnica.
- **JSON válido:** o texto (ou o bloco `<json>` no T3) é um objeto JSON; única tolerância: cerca de markdown ao redor.
- **Custo:** tokens de entrada e saída informados pela API × preço de tabela de `config/precos.json` (US$ 0,10 e US$ 0,50 por 1M de tokens, consultado em 2026-11-19 em https://platform.claude.com/docs/en/about-claude/pricing). Custo por acerto = custo total da técnica / respostas corretas. Tokens de raciocínio contam como saída.
- **Latência:** `time.perf_counter` em volta da chamada bem-sucedida; média e mediana.
- **Intervalo de confiança de 95%:** bootstrap percentil, 10.000 reamostragens dos 50 casos, seed 42. Intervalos que se sobrepõem não geram declaração de vencedor.
- **Modelo:** `claude-haiku-5-5` (Anthropic, SDK oficial). Cada rodada: 4 técnicas × 50 casos × 3 repetições = 600 respostas; todas com `stop_reason = end_turn` e nenhuma precisou de retry.

## Resultados da rodada v1 (oficial, `resultados/RELATORIO.md`)

| Técnica | Prompt | Acerto por caso (média) | IC 95% | Mín–máx entre repetições | JSON válido | Custo por caso (US$) | Custo por acerto (US$) | Latência média / mediana (s) |
|---|---|---|---|---|---|---|---|---|
| T1 zero-shot | v1 `1ef67d6a52fc` | 95.3% | 89.3%–100.0% | 94.0%–96.0% | 100.0% | 0.000108 | 0.000114 | 1.32 / 1.21 |
| T2 few-shot | v1 `be0e8998a563` | 98.0% | 94.0%–100.0% | 98.0%–98.0% | 100.0% | 0.000143 | 0.000146 | 1.14 / 0.97 |
| T3 chain-of-thought | v1 `b3a7a7a94ceb` | 97.3% | 92.7%–100.0% | 96.0%–98.0% | 100.0% | 0.000330 | 0.000339 | 3.17 / 3.06 |
| T4 system prompt | v1 `bb14abcde430` | 90.0% | 82.0%–98.0% | 90.0%–90.0% | 100.0% | 0.000126 | 0.000140 | 1.20 / 1.02 |

As 29 respostas erradas têm a mesma causa: o texto de cinco casos traz "Papelaria Aurora Ltda." com um ponto de separador de frase que o meu gerador inseriu, e o gabarito não tem ponto. Os modelos copiaram a abreviação correta. É **artefato do caso, não erro de modelo**. Na recontagem pós-hoc (não oficial) as quatro técnicas chegam a 100% (`resultados/ERROS.md`). Mantive o resultado oficial, porque mudar a regra depois de ver o resultado quebraria o congelamento. Conclusão da v1: acerto entre 90,0% e 98,0%, intervalos que se sobrepõem, **nenhuma técnica declarada melhor**; a tarefa ficou fácil demais.

## Resultados da rodada v2 (oficial, `resultados/v2/RELATORIO.md`)

| Técnica | Prompt | Acerto por caso (média) | IC 95% | Mín–máx entre repetições | JSON válido | Custo por caso (US$) | Custo por acerto (US$) | Latência média / mediana (s) |
|---|---|---|---|---|---|---|---|---|
| T1 zero-shot | v1 `1ef67d6a52fc` | 98.7% | 96.7%–100.0% | 96.0%–100.0% | 100.0% | 0.000125 | 0.000127 | 1.42 / 1.33 |
| T2 few-shot | v1 `be0e8998a563` | 92.7% | 84.7%–98.7% | 92.0%–94.0% | 100.0% | 0.000163 | 0.000176 | 1.31 / 1.10 |
| T3 chain-of-thought | v1 `b3a7a7a94ceb` | 100.0% | 100.0%–100.0% | 100.0%–100.0% | 100.0% | 0.000351 | 0.000351 | 3.29 / 3.21 |
| T4 system prompt | v1 `bb14abcde430` | 92.0% | 84.0%–98.0% | 92.0%–92.0% | 100.0% | 0.000160 | 0.000174 | 1.51 / 1.24 |

- **T3 (chain-of-thought) ficou acima de T2 e T4**, com intervalos de 95% que não se sobrepõem. Contra T1 os intervalos se sobrepõem, então não há declaração.
- **Todas as 25 respostas erradas estão no tipo `valor_total`** (4 casos × 3 repetições = 12 respostas por técnica). Nos outros 46 casos as quatro técnicas acertam 100% (recontagem pós-hoc em `resultados/v2/ERROS.md`).
- **O que aconteceu nesse tipo:** o texto traz só o total ("valor total US$ 350,00" para 10 caixas) e o gabarito exige dividir (35). T3 calculou em 12 de 12; T1 em 10 de 12; T2 devolveu `null` em 11 de 12; T4 devolveu `null` em 12 de 12. Em todos os erros o valor foi `null`; nenhuma resposta devolveu o total como se fosse o unitário.
- **Causa provável:** o prompt T4 diz "se uma informação não estiver no texto, use null" e "não invente valores", e ele seguiu a própria regra. Os 3 exemplos do T2 trazem sempre o preço unitário explícito, e ele provavelmente repetiu esse padrão (hipótese, não testei). Com outro gabarito ("deixe null quando só há o total"), o ranking nesse tipo se inverteria.
- **Consequência:** a vantagem do T3 vem de 4 casos de um único tipo e de uma regra de rotulagem minha que os prompts não mencionam. É um resultado sobre **como cada prompt trata um dado implícito**, não uma medida geral de qualidade.
- **Custo e tempo (v2):** custo por caso T1 US$ 0,000125, T2 US$ 0,000163, T3 US$ 0,000351, T4 US$ 0,000160; o T3 custou 2,8 vezes o T1 e levou 2,3 vezes mais tempo. Na v1 a razão de custo foi 3,0 vezes, sem ganho de acerto.

## Custo gasto

US$ 0.227230 de um teto de US$ 1,00: v1 (piloto de 10 chamadas mais 600) US$ 0.107289 e v2 (600 chamadas) US$ 0.119941, conforme o livro-caixa do cliente. O cliente reserva o custo máximo antes de cada chamada e para com erro registrado se a próxima passaria do teto (testado em `tests/test_custo_e_cliente.py`).

## Por que isso importa para um time de negócio

- Para extrair dados de texto livre, um modelo pequeno acertou ao menos 90,0% dos casos com qualquer técnica, nas duas rodadas, e 100% dos 46 casos da v2 que não envolvem cálculo.
- **A regra de negócio vale mais que a técnica.** O que separou as técnicas foi uma pergunta que a empresa precisa responder e escrever no prompt (quando só há o total, calcular ou deixar vazio?).
- Pagar por raciocínio passo a passo custou cerca de 3 vezes mais por caso (2,8 na v2 e 3,0 na v1); só trouxe ganho de acerto onde havia cálculo implícito.
- Antes de escolher a técnica mais cara, vale medir com casos do seu próprio problema. Vale para esta tarefa e este modelo; não é regra geral.

## Limitações

- **Só 50 casos por rodada** (duas rodadas, v1 e v2), de textos gerados por modelos de frase, mais regulares que e-mails reais. Na v2, a diferença entre técnicas vem de 4 casos de um único tipo.
- **Um modelo só** (`claude-haiku-5-5`); não comparei provedores.
- **O gabarito foi criado pelo autor do projeto, não por outra pessoa**; não há concordância entre anotadores. Na v2 as regras novas (como calcular o valor unitário a partir do total) são decisões do autor e decidem o resultado do único tipo em que houve diferença.
- **A v2 foi desenhada depois de ver a v1**, para corrigir o artefato e dificultar a tarefa; não é uma segunda medição independente.
- **Sem temperatura 0:** o modelo não aceita `temperature`. A variação foi medida por 3 repetições, que não provam determinismo.
- **Raciocínio do modelo:** o raciocínio adaptativo vem ligado por padrão; fixei `effort = "low"`. Todas as técnicas podem raciocinar internamente, o que dilui a diferença da chain-of-thought.
- Resultados não generalizáveis para outras tarefas, idiomas ou modelos.

## Como rodar

```bash
git clone https://github.com/Prodigyb0y/prompt-engineering
cd prompt-engineering
python -m venv .venv && .venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\python.exe -m pip ...
.venv/bin/python -m pytest -q                       # testes que não chamam API
cp .env.example .env                                # preencha ANTHROPIC_API_KEY (nunca versione o .env)
.venv/bin/python src/rodar.py --piloto              # 10 chamadas
.venv/bin/python src/rodar.py --completo            # v1: 600 chamadas, retomável
PE_VERSAO=v2 .venv/bin/python src/rodar.py --completo   # v2 (PowerShell: $env:PE_VERSAO="v2")
.venv/bin/python src/analisar.py                    # resultados/RELATORIO.md e resumo.json (com PE_VERSAO=v2: resultados/v2/)
.venv/bin/python src/classificar_erros.py           # ERROS.md
.venv/bin/python src/gerar_demo.py                  # docs/index.html (com PE_VERSAO=v2: docs/v2/)
```

Os resultados brutos (`resultados/brutos/`, `resultados/v2/brutos/`) não vão para o Git. Quem refizer as rodadas pode obter números diferentes, porque o modelo não aceita temperatura 0.

## Estrutura

`dados/` e `dados/v2/` casos, gabarito e exemplos (fictícios) · `prompts/` quatro prompts v1 · `src/` geradores, validadores, cliente com teto, custo, execução, análise, demo · `tests/` testes sem API · `config/precos.json` · `resultados/` e `resultados/v2/` relatórios gerados · `docs/` demos e checklist.

## Decisões registradas durante a execução

- **Sem temperatura 0 (2026-11-19).** O `claude-haiku-5-5` não aceita `temperature`, `top_p` nem `top_k`; a primeira tentativa de piloto falhou no SDK antes de qualquer chamada paga (custo zero).
- **Raciocínio adaptativo ligado por padrão.** Fixei `effort = "low"` para limitar o raciocínio oculto e o custo. Registrado em cada resultado bruto.
- **Artefato do "Ltda."** descoberto depois da rodada v1; resultado oficial mantido, recontagem pós-hoc separada, dados v2 gerados sem o artefato.
- **O tipo `valor_total` da v2** concentrou todos os erros; resultado oficial mantido, causa e recontagem sem o tipo documentadas.

## Próximos passos

- Prompts v2 de T1–T4 com a regra de negócio escrita ("se só houver o valor total, calcule o unitário" e a regra oposta), mantendo as v1 nos relatórios, para medir quanto da diferença é regra e quanto é técnica.
- Mais casos por tipo (hoje 4 de `valor_total`) para a comparação ter força estatística.
- Segunda pessoa para rotular o gabarito e medir concordância.
- Comparar com outro modelo, se houver orçamento.
