# Checklist de entrega

Verificado no commit `355ba94` (este arquivo entra no commit seguinte). Só está marcado o que foi verificado; o resto fica em aberto com o motivo.

- [x] **README completo.** Teste confere que a tabela do README é idêntica à de `resultados/RELATORIO.md` e que as limitações obrigatórias estão declaradas (`tests/test_readme.py`).
- [x] **Dados fictícios.** Gerados por script com seed 42, empresa fictícia Gutenberg Systems; nomes de fornecedores inventados. Não verifiquei se algum nome coincide com empresa real.
- [x] **Medida de acerto.** Regra escrita antes de medir (`src/validador.py`), 600 respostas, IC 95% por bootstrap (`resultados/RELATORIO.md`).
- [x] **Custo.** Tokens da API × preço de tabela de `config/precos.json` (fonte e data registradas); gasto total US$ 0,107289 de US$ 1,00.
- [x] **Latência.** `time.perf_counter`, média e mediana por técnica.
- [x] **Frase de impacto** no topo do README.
- [x] **Teto de gasto no código.** O cliente reserva o custo máximo antes de cada chamada e bloqueia com erro registrado; testado sem chamar a API.
- [x] **pytest passando.** 46 testes passando neste commit (ambiente de desenvolvimento, Python 3.13). No computador do autor (Python 3.11) passaram 34 testes antes dos testes novos de análise, demo e README; os 46 não foram rodados lá.
- [x] **Nenhuma chave no Git.** Busca por `sk-ant-` seguido de 20 ou mais caracteres em todo o histórico (11 commits): 0 ocorrências. `.env` não está versionado (só `.env.example`).
- [x] **Página da demo funciona sem instalação.** `docs/index.html` abre direto e renderizou sem erro de JavaScript em Chrome sem interface; tabela e explorador de casos conferidos.
- [ ] **Demo publicada em GitHub Pages.** Não verificado: a publicação precisa ser ativada nas configurações do repositório (Settings → Pages → branch `main`, pasta `/docs`). Também não foi testada em janela anônima.
- [ ] **Repositório público confirmado de forma independente.** O autor clonou sem erro, mas não conferi sem credenciais.
- [ ] **Rodada refeita sem o artefato do "Ltda.".** Não feito (ver "Próximos passos" no README).
