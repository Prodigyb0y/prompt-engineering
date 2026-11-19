# Laboratório de prompt engineering

**Mesma tarefa, mesmos casos, quatro técnicas de prompt: o que acerta mais, e quanto custa cada acerto.**

Projeto de portfólio. É uma recriação conceitual com **dados 100% fictícios** (empresa fictícia Gutenberg Systems). Não há dados, nomes, sistemas ou documentos de nenhuma empresa real.

## O problema

Times de negócio gastam tempo corrigindo à mão dados extraídos de textos livres (pedidos de compra, e-mails). Escolher a técnica de prompt por intuição sai caro, e ninguém sabe se valeu a pena. Este projeto mede, na mesma tarefa, quanto cada técnica acerta e quanto custa.

**Quem usa:** um time de compras (ou de operações) que recebe solicitações em texto livre e precisa delas como campos estruturados.

## Resultado em uma frase

Nesta tarefa, as quatro técnicas ficaram entre 90,0% e 98,0% de acerto por caso, **com intervalos de confiança que se sobrepõem, então não declaro nenhuma vencedora**. O que separa as técnicas é o custo: a chain-of-thought custou cerca de 3.0 vezes o custo por caso da zero-shot e levou cerca de 2.4 vezes mais tempo, sem ganho de acerto mensurável. Os números abaixo vêm de `resultados/RELATORIO.md`; as razões são calculadas de `resultados/resumo.json`.

## Demo

**https://prodigyb0y.github.io/prompt-engineering/** (GitHub Pages, gerada de [`docs/index.html`](docs/index.html)). Página estática, sem servidor, sem instalação e sem chave: tabela por técnica e explorador dos 50 casos (texto, gabarito e saída de cada técnica, por repetição). Também abre direto do arquivo no navegador. Carregamento confirmado pelo autor em 2026-11-19; o teste em janela anônima ainda não foi registrado.

## A tarefa e os dados (fictícios)

A partir de uma mensagem livre de solicitação de compra, extrair um JSON com 8 campos: `solicitante_area`, `item`, `quantidade`, `unidade` (`un`, `kg`, `m`, `l`, `cx`), `prazo_entrega` (AAAA-MM-DD ou null), `valor_unitario`, `moeda` (`BRL`, `USD`, `EUR` ou null) e `fornecedor`.

- 50 casos em 10 tipos: completa, campos faltando, unidades variadas, valor brasileiro (`R$ 1.200,00`), moeda por símbolo, formatos de data, data relativa (vira null), apelido de fornecedor, ruído e erro de digitação, duas quantidades.
- Gabarito gerado por script (seed 42) a partir de registro estruturado, **congelado antes da primeira execução** (hashes em `dados/CONGELADO.sha256`, conferidos por teste).
- 3 exemplos few-shot separados, que não repetem nenhum caso de teste.
- Validação: script que relê data, valor e moeda do texto de forma independente e compara com o gabarito; 10 casos sorteados revisados à mão (10 de 10 corretos). Detalhes em `dados/REVISAO_E_LIMITACOES.md`.

## As quatro técnicas (v1, cada uma com hash do texto)

| Id | Técnica | O que muda |
|---|---|---|
| T1 | zero-shot | instrução e schema, sem exemplos |
| T2 | few-shot | instrução, schema e 3 exemplos fixos |
| T3 | chain-of-thought | raciocínio em `<raciocinio>` e JSON em `<json>`; só o `<json>` é lido |
| T4 | system prompt | papel, regras e formato no system prompt, sem exemplos |

Os prompts estão em `prompts/` (JSON com versão e SHA-256 de 12 caracteres) e são iguais para todos os casos. Nenhum prompt foi alterado depois de ver resultado.

## Como cada métrica foi medida

- **Acerto por caso:** JSON válido, schema pydantic válido (`extra="forbid"`) e os 8 campos iguais ao gabarito. Normalização definida antes de medir: texto sem acento, minúsculo e espaços colapsados; números exatos; datas ISO; null só igual a null. Média sobre 3 repetições, com mínimo e máximo entre as repetições.
- **Acerto por campo e por tipo:** média sobre todas as respostas da técnica.
- **JSON válido:** o texto (ou o bloco `<json>` no T3) é um objeto JSON; única tolerância: cerca de markdown ao redor.
- **Custo:** tokens de entrada e saída informados pela API × preço de tabela de `config/precos.json` (US$ 0,10 e US$ 0,50 por 1M de tokens, consultado em 2026-11-19 em https://platform.claude.com/docs/en/about-claude/pricing). Custo por acerto = custo total da técnica / respostas corretas. Os tokens de raciocínio contam como saída.
- **Latência:** `time.perf_counter` em volta da chamada bem-sucedida; média e mediana.
- **Intervalo de confiança de 95%:** bootstrap percentil, 10.000 reamostragens dos 50 casos, seed 42. Intervalos que se sobrepõem não geram declaração de vencedor.
- **Modelo:** `claude-haiku-5-5` (Anthropic, SDK oficial). 4 técnicas × 50 casos × 3 repetições = 600 respostas, todas com `stop_reason = end_turn`, nenhuma precisou de retry.

## Resultados (oficial, de `resultados/RELATORIO.md`)

| Técnica | Prompt | Acerto por caso (média) | IC 95% | Mín–máx entre repetições | JSON válido | Custo por caso (US$) | Custo por acerto (US$) | Latência média / mediana (s) |
|---|---|---|---|---|---|---|---|---|
| T1 zero-shot | v1 `1ef67d6a52fc` | 95.3% | 89.3%–100.0% | 94.0%–96.0% | 100.0% | 0.000108 | 0.000114 | 1.32 / 1.21 |
| T2 few-shot | v1 `be0e8998a563` | 98.0% | 94.0%–100.0% | 98.0%–98.0% | 100.0% | 0.000143 | 0.000146 | 1.14 / 0.97 |
| T3 chain-of-thought | v1 `b3a7a7a94ceb` | 97.3% | 92.7%–100.0% | 96.0%–98.0% | 100.0% | 0.000330 | 0.000339 | 3.17 / 3.06 |
| T4 system prompt | v1 `bb14abcde430` | 90.0% | 82.0%–98.0% | 90.0%–90.0% | 100.0% | 0.000126 | 0.000140 | 1.20 / 1.02 |

Acerto por campo, por tipo, tokens e a classificação dos erros estão em `resultados/RELATORIO.md` e `resultados/ERROS.md`.

### O que explica os erros (leia antes de comparar)

As 29 respostas erradas têm a mesma causa: o texto de cinco casos traz o fornecedor como "Papelaria Aurora Ltda." com um ponto de separador de frase que o meu gerador de casos inseriu, e o gabarito não tem ponto. Os modelos copiaram "Ltda." com o ponto, que é a abreviação correta. É um **artefato do caso, não erro de modelo**. Na recontagem **pós-hoc** (feita depois de ver os resultados, por isso não oficial) as quatro técnicas chegam a 100% (`resultados/ERROS.md`). Mantive o resultado oficial como está, porque mudar a regra depois de ver o resultado quebraria a regra de congelar antes de medir. Não testei por que o T4 repetiu o ponto mais vezes que os outros.

Consequência prática: **esta tarefa ficou fácil demais para separar as técnicas em acerto.** A comparação que se sustenta nos dados é de custo e latência.

## Custo gasto

US$ 0.107289 de um teto de US$ 1,00 (piloto de 10 chamadas mais as 600 da rodada completa), conforme o livro-caixa do cliente, impresso no fim de `resultados/RELATORIO.md`. O cliente reserva o custo máximo antes de cada chamada e para com erro registrado se a próxima passaria do teto (testado em `tests/test_custo_e_cliente.py`).

## Por que isso importa para um time de negócio

Em uma extração simples, um modelo pequeno acertou ao menos 90,0% dos casos com qualquer técnica. Pagar por raciocínio passo a passo triplicou o custo por caso e mais que dobrou a espera sem melhorar o acerto nesta medição; incluir 3 exemplos custou cerca de 32% a mais por caso. Antes de escolher a técnica mais cara, vale medir com casos do seu próprio problema. Isto vale para esta tarefa e este modelo; não é uma regra geral.

## Limitações

- **Só 50 casos**, de textos gerados por modelos de frase fixos, mais regulares que e-mails reais.
- **Um modelo só** (`claude-haiku-5-5`); não comparei provedores.
- **O gabarito foi criado pelo autor do projeto, não por outra pessoa**; não há concordância entre anotadores.
- **Sem temperatura 0:** o modelo não aceita `temperature`. A variação foi medida por 3 repetições, que não provam determinismo.
- **Raciocínio do modelo:** o raciocínio adaptativo vem ligado por padrão; fixei `effort = "low"`. Todas as técnicas podem raciocinar internamente, o que dilui a diferença da chain-of-thought.
- **Teto de acerto:** a tarefa ficou fácil e o artefato do "Ltda." domina os erros, então o projeto não consegue ordenar as técnicas por acerto.
- **Regras do T4 espelham as regras de rotulagem que o mesmo autor escreveu no gabarito**, o que o favorece.
- Resultados não generalizáveis para outras tarefas, idiomas ou modelos.

## Como rodar

```bash
git clone https://github.com/Prodigyb0y/prompt-engineering
cd prompt-engineering
python -m venv .venv && .venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\python.exe -m pip ...
.venv/bin/python -m pytest -q                       # testes que não chamam API
cp .env.example .env                                # preencha ANTHROPIC_API_KEY (nunca versione o .env)
.venv/bin/python src/rodar.py --piloto              # 10 chamadas
.venv/bin/python src/rodar.py --completo            # 600 chamadas, retomável
.venv/bin/python src/analisar.py                    # resultados/RELATORIO.md e resumo.json
.venv/bin/python src/classificar_erros.py           # resultados/ERROS.md
.venv/bin/python src/gerar_demo.py                  # docs/index.html
```

Os resultados brutos (`resultados/brutos/`) não vão para o Git. Quem refizer a rodada pode obter números diferentes, porque o modelo não aceita temperatura 0.

## Estrutura

`dados/` casos, gabarito e exemplos (fictícios) · `prompts/` quatro prompts v1 · `src/` gerador, validador, cliente com teto, custo, execução, análise, demo · `tests/` testes sem API · `config/precos.json` · `resultados/` relatórios gerados · `docs/` demo e checklist.

## Decisões registradas durante a execução

- **Sem temperatura 0 (2026-11-19).** O `claude-haiku-5-5` não aceita `temperature`, `top_p` nem `top_k`; a primeira tentativa de piloto falhou no SDK antes de qualquer chamada paga (custo zero).
- **Raciocínio adaptativo ligado por padrão.** Fixei `effort = "low"` para limitar o raciocínio oculto e o custo. Registrado em cada resultado bruto.
- **Artefato do "Ltda."** descoberto depois da rodada completa; resultado oficial mantido, recontagem pós-hoc separada.

## Próximos passos

- Gerar uma versão 2 dos dados sem o artefato de pontuação e com casos mais difíceis (e-mails longos, campos ambíguos), congelar de novo e repetir a rodada (nova versão, relatando a v1 também).
- Segunda pessoa para rotular o gabarito e medir concordância.
- Testar prompts v2 de T3 e T4 como versões novas, sem apagar a v1.
- Comparar com outro modelo, se houver orçamento.
