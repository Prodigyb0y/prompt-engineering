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
- [x] **`pytest` passando.** 123 testes, neste ambiente (Python 3.x do sandbox), sem chamar a API.
- [x] **Nenhuma chave no histórico.** Busca por `sk-ant-` seguido de 20 ou mais caracteres em todo o histórico Git e na árvore: 0 ocorrências. `.env` não é versionado.
- [x] **Acerto e custo medidos para o P1 e para os experimentos E1 e E2** (rodadas v1 e v2 e iteração do T4, números inalterados, auditados em `resultados/extracao/*/AUDITORIA.md`).
- [ ] **Acerto e custo medidos para P2 a P5 e experimentos E3, E4 e E5.** **Não feito:** as rodadas pagas (piloto de 5 chamadas por prompt e rodada completa, teto de US$ 0,60) dependem da chave da API do autor, que não existe neste ambiente. Pipeline pronto e testado; comandos no README. Até lá, a demo e o README mostram "não medido". Gasto total até aqui: US$ 0,248969 de US$ 1,00.
- [ ] **Demo aberta pelo endereço público nesta versão.** Depende do push e da publicação do GitHub Pages.
- [ ] **Segunda pessoa conferindo os gabaritos.** Não feito; limitação declarada.
- [ ] **Validação do T4 v2 em casos novos.** Não feita; a regra foi escrita olhando os mesmos 50 casos.
