# Dados fictícios: método, revisão e limitações

Tudo aqui é fictício (empresa fictícia Gutenberg Systems; fornecedores e áreas inventados).

## Como foi gerado
`python src/gerar_dados.py` (seed 42). Cada caso nasce de um registro estruturado; o gabarito sai do registro e o texto é renderizado a partir dele. Nenhum modelo de linguagem participou da criação dos dados ou do gabarito.

## Regras de rotulagem (valem para o gabarito)
- `fornecedor`: nome exatamente como aparece no texto. Apelido não é expandido (ex.: "Vale Verde" fica "Vale Verde").
- Data relativa ("daqui 15 dias", "em 10 dias úteis") vira `prazo_entrega = null`.
- `valor_unitario` e `moeda` são ambos null ou ambos preenchidos.
- Com duas quantidades no texto, vale a do item pedido (a outra é distrator).
- As regras de normalização para comparação (P-01) ainda serão escritas antes de qualquer medição.

## Validação
`python src/validar_dados.py` relê data, valor e moeda do texto com regex independentes do gerador e compara com o gabarito; confere enums, cobertura dos 10 tipos, textos únicos e que os 3 exemplos few-shot não repetem nenhum caso de teste. Resultado em 2026-11-19: OK.

## Revisão manual (2026-11-19)
10 casos sorteados com seed 42: C01, C04, C11, C20, C21, C24, C26, C30, C35, C49. Conferi texto contra gabarito campo a campo: 10 de 10 corretos, sem divergência.
Limite da revisão: ela cobre 10 dos 50 casos; os outros 40 foram verificados só pelo script.

## Limitações (declarar no README)
- O gabarito foi criado pelo autor do projeto, não por outra pessoa; não há concordância entre anotadores.
- Os textos vêm de modelos de frase fixos, então são mais regulares que e-mails reais.
- Não há medição de acerto de nenhuma técnica ainda.

## Congelamento
Hashes SHA-256 em `dados/CONGELADO.sha256`. Se `gabarito.json` ou `casos_teste.json` mudar depois da primeira execução, registrar a mudança aqui e rodar tudo de novo.
