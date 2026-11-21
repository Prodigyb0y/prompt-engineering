# Diagnóstico dos erros (feito depois da medição, sem chamar a API)

Gerado por `python src/diagnostico.py` a partir de `resultados/biblioteca/brutos/`. As regras de acerto oficiais não mudaram; a "reanálise por pedido" do P3 é uma regra auxiliar, escrita depois de ler os erros, e só serve para explicar o resultado (veja o docstring do script).

## P3 / E4: por que o acerto foi o menor

Extração do P1 correta (os 8 campos iguais ao gabarito) em 60 de 60 respostas do fluxo encadeado.

| Fluxo | Respostas | Erradas (oficial) | Pediu campo que já tinha | Só confirmou dado recebido | Esqueceu campo | Acerto oficial | Acerto pela reanálise por pedido |
|---|---|---|---|---|---|---|---|
| Encadeado (P1 → P3) | 60 | 13 | 4 | 9 | 0 | 78,3% | 93,3% |
| Prompt único | 60 | 11 | 9 | 2 | 0 | 81,7% | 85,0% |

Erros do encadeado em que a extração do P1 estava errada: 0 de 13.
Erros do prompt único em que o e-mail pediu a área solicitante e a área era "Compras": 9 de 11.

## E3: onde o zero-shot errou

| Variante | Respostas | Erradas | Campo errado | Urgência esperada → obtida |
|---|---|---|---|---|
| Zero-shot | 60 | 5 | urgencia: 5 | media → baixa (5) |
| Few-shot | 60 | 1 | urgencia: 1 | alta → media (1) |

## E5: onde a resposta direta errou

| Variante | Respostas | Erradas | Erros (caso, tipo, esperada → obtida, vezes) |
|---|---|---|---|
| Sem raciocínio | 60 | 3 | A19 (escalar_fornecedor_e_item), escalar → duas respostas (pedir_informacao → escalar), 1x; A19 (escalar_fornecedor_e_item), escalar → pedir_informacao, 2x |
| Com raciocínio | 60 | 0 | — |

## P4: onde errou

3 de 60 respostas erradas; campo errado: sentimento: 3. Sentimento esperado → obtido: neutro → insatisfeito (2); irritado → insatisfeito (1). Invenções de número ou valor: 0.
