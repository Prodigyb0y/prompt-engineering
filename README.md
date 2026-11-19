# Laboratório de prompt engineering

Mesma tarefa, mesmos casos, quatro técnicas de prompt: o que acerta mais, e quanto custa cada acerto.

> Status: em construção. Dados, prompts, validador, cliente com teto de gasto e testes prontos; nenhuma chamada paga feita e nenhum resultado medido ainda. Dados 100% fictícios (empresa fictícia Gutenberg Systems).

## Decisões registradas durante a execução

- **Sem temperatura 0 (2026-11-19).** O `claude-haiku-5-5` não aceita `temperature`, `top_p` nem `top_k`; a primeira tentativa de piloto falhou no SDK antes de qualquer chamada paga (custo zero). A variação entre execuções é medida pelas 3 repetições, e o README não pode afirmar determinismo.
- **Raciocínio adaptativo ligado por padrão no modelo.** Fixei `effort = "low"` para limitar o raciocínio oculto. Isso afeta o custo (tokens de raciocínio contam como saída) e a comparação com a técnica chain-of-thought: todas as técnicas podem raciocinar internamente. Está registrado em cada resultado bruto.
