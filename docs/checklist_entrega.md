# Checklist de entrega

Verificado na árvore de trabalho; as alterações mais recentes entram no commit seguinte ao último listado no histórico. Só está marcado o que foi verificado; o resto fica em aberto com o motivo.

- [x] **README completo**, em estrutura padrão (resumo, demo, dados, técnicas, métricas, resultados, limitações, auditoria, como rodar, estrutura, próximos passos), com as duas rodadas (v1 e v2). Testes conferem que as tabelas do README são idênticas às de `resultados/RELATORIO.md` e `resultados/v2/RELATORIO.md` e que as limitações obrigatórias estão declaradas (`tests/test_readme.py`).
- [x] **Dados fictícios.** Gerados por script com seed 42, empresa fictícia Gutenberg Systems; nomes de fornecedores inventados. Não verifiquei se algum nome coincide com empresa real.
- [x] **Gabarito congelado antes de cada execução** (v1 e v2), com hashes conferidos por teste. A v2 foi desenhada depois de ver a v1, e isso está declarado.
- [x] **Medida de acerto.** Regra escrita antes de medir (`src/validador.py`); v1 e v2 com 600 respostas cada, IC 95% por bootstrap.
- [x] **Custo.** Tokens da API × preço de tabela de `config/precos.json` (fonte e data registradas); gasto total US$ 0,248969 de US$ 1,00.
- [x] **Latência.** `time.perf_counter`, média e mediana por técnica.
- [x] **Frase de impacto** no topo do README.
- [x] **Teto de gasto no código.** O cliente reserva o custo máximo antes de cada chamada e bloqueia com erro registrado; testado sem chamar a API.
- [x] **pytest passando.** 62 testes passando neste ambiente de desenvolvimento (Python 3.13). No computador do autor (Python 3.11) passaram 34 testes numa versão anterior; os atuais não foram rodados lá.
- [x] **Nenhuma chave no Git.** Busca por `sk-ant-` seguido de 20 ou mais caracteres em todo o histórico e na árvore: 0 ocorrências. `.env`, `logs/` e os resultados brutos não estão versionados.
- [x] **Rodada v2 íntegra.** Dados v2 batem com os hashes congelados, os prompts mantêm os hashes da v1, 600 respostas, todas `end_turn`, nenhuma com retry.
- [ ] **Demo única aberta pelo endereço público.** https://prodigyb0y.github.io/prompt-engineering/ passou a mostrar a rodada v2 com a iteração (a v1 foi retirada da demo e segue descrita no README); a abertura nesta versão ainda não foi verificada. O autor abriu a versão anterior em janela anônima em 2026-11-19.
- [x] **Página da demo funciona.** `docs/index.html` renderizou sem erro de JavaScript em Chrome sem interface, em tela larga e estreita, sem rolagem horizontal; numeração das seções em sequência.
- [x] **Auditoria independente das duas rodadas.** `src/auditar.py` recalculou acerto e custo das respostas brutas e reavaliou as 1.200 respostas: 0 divergências (`resultados/AUDITORIA.md`, `resultados/v2/AUDITORIA.md`).
- [x] **Critério de vencedor corrigido.** A declaração "T3 acima de T2 e T4" na v2 foi retirada: o intervalo bootstrap de 100% tem largura zero e o teste do sinal exato dá p = 0,125. Registrado no README (seção "Auditoria e decisões registradas") e coberto por testes em `tests/test_analise.py`.
- [x] **Anatomia do prompt na demo.** Seção que divide o system prompt do T4 em partes, com o texto real, a função de cada uma e o tipo de caso que cobre (gerada do arquivo do prompt; falha se a estrutura mudar).
- [x] **Iteração T4 v1 → v2 executada.** 150 chamadas, 100,0% contra 92,0% na v1, sem regressão, p = 0,125 (sem significância); resultado de desenvolvimento, não de generalização. Detalhes em `resultados/v2/ITERACAO.md`.
- [ ] **Repositório público confirmado de forma independente.** O autor clonou e abriu o Pages sem erro, mas não conferi sem credenciais.
- [ ] **Segunda pessoa conferindo o gabarito.** Não feito; limitação declarada.
- [ ] **Validação do T4 v2 em casos novos.** Não feita; fora do escopo desta entrega e registrada em "Próximos passos" no README.
