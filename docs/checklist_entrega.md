# Checklist de entrega

Verificado na árvore de trabalho a partir do commit-base `1717963`; as alterações desta versão entram no commit que a publica (veja `git log`). Só está marcado o que foi verificado; o resto fica em aberto com o motivo.

- [x] **Repositório organizado em "biblioteca + experimentos".** `prompts/` (P1 a P5 e controles), `dados/biblioteca/` e `dados/extracao/`, `resultados/`, `src/`, `tests/`, `docs/`. Evidência antiga preservada (movida, não apagada); hashes de congelamento continuam batendo (testes). Mapa de caminhos em `docs/medicao.md`.
- [x] **README completo**, na ordem pedida (título e demo, o que mostra, biblioteca, P1 completo, antes e depois, experimentos, importância para o negócio, limitações, como rodar e estrutura, apêndice). Gerado por `src/gerar_docs.py` a partir de `resultados/resumo.json`; `tests/test_readme.py` confere ordem, números e links.
- [x] **Demo sem instalação e sem chave.** `docs/index.html` é um arquivo único (CSS e JS embutidos, sem CDN), gerado por `src/gerar_demo.py`. Abri em Chrome sem interface, nos temas escuro e claro e em tela de celular: sem erro de JavaScript e sem rolagem horizontal. Capturas em `docs/img/`.
- [x] **Dados fictícios.** Gerados por script com seed fixa, empresa fictícia Gutenberg Systems. Não verifiquei se algum nome inventado coincide com empresa real.
- [x] **Gabaritos congelados antes de rodar.** P2 a P5 (20 casos cada) e extração v1 e v2, com SHA-256 conferido por teste. Revisão manual de 5 casos por prompt feita por mim, não por uma segunda pessoa (`dados/biblioteca/REVISAO_E_LIMITACOES.md`).
- [x] **Regras de acerto escritas antes de rodar**, em código (`src/avaliadores.py`), com testes que não chamam a API.
- [x] **Frase de impacto** no topo do README e da demo.
- [x] **Teto de gasto testado.** O cliente reserva o custo máximo antes de cada chamada e bloqueia com erro registrado; teto próprio de US$ 0,60 para as rodadas novas e US$ 1,00 no total, testado sem chamar a API (`tests/test_biblioteca_avaliacao_e_execucao.py`).
- [x] **`pytest` passando.** 123 testes, sem chamar a API: passam neste ambiente e, após dois ajustes (comparação de decimais e varredura de chave que lia o `.env` local), passam também no Windows do autor segundo a execução dele, que acusou só esses dois.
- [x] **Nenhuma chave no histórico.** Busca por `sk-ant-` seguido de 20 ou mais caracteres em todo o histórico Git e na árvore: 0 ocorrências. `.env` não é versionado.
- [x] **Acerto e custo medidos para o P1 e para os experimentos E1 e E2** (rodadas v1 e v2 e iteração do T4, números inalterados, auditados em `resultados/extracao/*/AUDITORIA.md`).
- [x] **Acerto e custo medidos para P2 a P5 e experimentos E3, E4 e E5.** Piloto de 5 chamadas por prompt (US$ 0,003544) e rodada completa (20 casos, 3 repetições, 420 respostas, US$ 0,081495), executados pelo autor no computador dele; gasto novo US$ 0,085039 de US$ 0,60 e total US$ 0,334008 de US$ 1,00. Respostas brutas em `resultados/biblioteca/brutos/`; relatório em `resultados/biblioteca/RELATORIO.md`. Diferenças pequenas com 20 casos: indício, não prova (declarado em cada experimento).
- [ ] **Demo aberta pelo endereço público nesta versão.** Não conferi: o ambiente em que trabalho bloqueia o domínio do GitHub Pages. O autor precisa abrir e confirmar.
- [ ] **Segunda pessoa conferindo os gabaritos.** Não feito; limitação declarada.
- [ ] **Validação do T4 v2 em casos novos.** Não feita; a regra foi escrita olhando os mesmos 50 casos.
