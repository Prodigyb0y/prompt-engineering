# Revisão e limitações dos dados de P2 a P5

Dados 100% fictícios (empresa fictícia Gutenberg Systems), gerados por `src/gerar_dados_biblioteca.py` com seed fixa (2027 + deslocamento por prompt). 20 casos por prompt. O gabarito foi escrito junto com cada caso (rótulo explícito no modelo de texto, ou regra em código no P5) e **nunca veio de um modelo de linguagem**. Congelado por SHA-256 antes de qualquer chamada paga (`CONGELADO.sha256` em cada pasta, conferido por teste).

## Quem revisou

A revisão manual abaixo foi feita pelo assistente de IA (Claude) que preparou o projeto, lendo os casos um a um, **não por uma segunda pessoa**. O autor do projeto ainda não revisou. Isso fica declarado como limitação: não há concordância entre anotadores.

## Validação por script

`python src/validar_dados_biblioteca.py` relê cada texto com regex, sem usar os modelos do gerador, e compara com o gabarito: campos que faltam (P3), número de pedido, valor, sentimento e ação (P4), decisão por uma segunda implementação da política com frações exatas (P5), enums, duplicatas, cobertura de categorias, casos de borda exigidos e ausência de nomes reais conhecidos. Resultado: 80 casos, 0 divergências depois das correções abaixo.

## Revisão manual (5 casos por prompt, escolhidos pelo risco de ambiguidade)

| Prompt | Casos | O que olhei | Resultado |
|---|---|---|---|
| P2 | S13, S15, S16, S18, S20 | Se o "certo" é defensável: VPN × permissão (S13), defeito físico × software (S15), perda de dados (S16), sala de servidores (S18), salário atrasado (S20) | Defensáveis, mas são convenções minhas (ver limitações). S04 tinha "Sou da Financeiro": corrigido. |
| P3 | E02, E09, E12, E16, E17 | Faltantes conforme as regras do P1 (data relativa conta como faltando; só valor total conta como informado) | Consistentes com o P1 v2. |
| P4 | R07, R12, R16, R17, R19 | Sentimento e ação contra as regras escritas no prompt | **Achei 9 textos inconsistentes com o meu próprio gabarito** (R12 `irritado` sem gatilho; R01, R04, R06, R07, R09, R11 e R18 `insatisfeito` sem nenhuma palavra de emoção). Corrigi os textos, não o critério, e a validação passou a conferir sentimento e ação. |
| P5 | A04, A07, A09, A12, A20 | Precedência (faltar dado vence), limite exato (R$ 5.000,00 não escala), conversão de dólar e euro | Corretos pela política escrita no prompt. |

## Limitações (valem para as rodadas de P2 a P5)

- **O gabarito é do autor do projeto**, e os casos ambíguos do P2 (por exemplo, VPN que cai contra permissão negada) refletem convenções que escolhi. Com outras convenções, o resultado mudaria.
- **P2: os exemplos do few-shot cobrem as mesmas famílias de ambiguidade de 6 dos 8 casos de borda** (S13, S14, S15, S17, S19, S20). O experimento mede se o modelo aprende uma convenção a partir de exemplos, **não** se generaliza para famílias novas. S16 e S18 são as famílias sem exemplo.
- **P3:** o acerto é conferido por nome exato de campo no e-mail (vocabulário controlado definido no próprio prompt). Não mede qualidade do texto nem se o tom foi o pedido.
- **P4:** o acerto exige campos iguais ao gabarito e resumo com até 20 palavras e sem números fora do texto. Não mede se o resumo é bom, só se não inventa números.
- **P5:** a política é curta (4 regras) e o gabarito é calculado por ela, então o teste mede obediência a uma regra escrita, não julgamento.
- **Só 20 casos por prompt**: diferenças de poucos casos não sustentam conclusão (ver Detalhes da medição).
- Não verifiquei se algum nome de fornecedor coincide com empresa real (só conferi uma lista curta de nomes conhecidos).
