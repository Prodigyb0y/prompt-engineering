"""Texto em linguagem de negócio da biblioteca e dos experimentos.

Regra: este arquivo não contém resultado medido. Frases com número são montadas por funções a partir do resumo;
frases de "o que aprendi" que dependem de medição só existem quando há medição (senão o texto diz que não foi medido).
O que está aqui como "aprendizado do projeto" foi verificado durante a preparação (dados e regras), e cada uma
dessas frases aponta para o arquivo onde se pode conferir.
"""

NOME = "Prompt Lab · Gutenberg Systems"
EMPRESA_NOTA = "Gutenberg Systems é uma empresa fictícia. Todos os dados são gerados por script, com seed fixa; não há dados, pessoas, sistemas ou documentos de nenhuma empresa real."
FRASE_IMPACTO = "Prompts de negócio que você pode ler, copiar e conferir: o texto completo, por que foi escrito assim, o que mudou quando experimentei e quanto custou."
REPO = "https://github.com/Prodigyb0y/prompt-engineering"
DEMO = "https://prodigyb0y.github.io/prompt-engineering/"

PROMPTS = {
    "P1": {
        "problema": "O time de compras recebe pedidos em texto livre (\"preciso de 10 caixas de papel A4, entrega até dia 15...\") e redigita tudo à mão em um sistema.",
        "quem_usa": "Time de compras e operações.",
        "tecnica_porque": "Papel, regras e formato ficam fixos no system prompt: o modelo devolve sempre os mesmos 8 campos em JSON, e cada regra de borda é uma linha que dá para ler e mudar.",
    },
    "P2": {
        "problema": "Pedidos de suporte interno chegam sem padrão. Alguém precisa decidir para qual fila vão e com que prioridade.",
        "quem_usa": "Central de suporte interno (TI, instalações e RH).",
        "tecnica_porque": "As definições de categoria e urgência não resolvem os empates (VPN contra permissão, defeito físico contra software). Os exemplos mostram a convenção da empresa para cada empate.",
        "aprendi_projeto": "Escrever as definições foi fácil; difícil foi decidir a convenção de cada empate. Foi isso que virou exemplo. (Convenções e limites: dados/biblioteca/REVISAO_E_LIMITACOES.md)",
    },
    "P3": {
        "problema": "Quando o pedido chega incompleto, alguém escreve um e-mail pedindo o que falta, e às vezes pede o que já foi informado.",
        "quem_usa": "Time de compras.",
        "tecnica_porque": "Este prompt recebe a saída do P1 (o JSON com campos null) e só se preocupa em escrever. O tom é escrito no prompt, não deixado ao acaso.",
        "aprendi_projeto": "Dar um nome fixo a cada campo dentro do prompt é o que permite conferir cada e-mail por regra em código, sem ler os e-mails um a um. (Regra de acerto: src/avaliadores.py)",
    },
    "P4": {
        "problema": "Reclamações longas precisam virar um resumo estruturado para o atendimento decidir o próximo passo, sem que o resumo invente número de pedido ou valor.",
        "quem_usa": "Atendimento ao cliente.",
        "tecnica_porque": "Campo ausente vira null, não um palpite (regras explícitas de \"não inventar\"), e o prompt diz o que fazer quando o texto não deixa claro o que deu errado.",
        "aprendi_projeto": "Ao escrever a regra de sentimento no prompt, vi que 9 dos meus 20 textos de teste não a seguiam. Corrigi os textos e passei a conferir o gabarito contra as regras do prompt por script: regra e gabarito têm de ser escritos juntos. (dados/biblioteca/REVISAO_E_LIMITACOES.md)",
    },
    "P5": {
        "problema": "Depois da extração, alguém aplica a política de compras (campos obrigatórios, limite de valor, fornecedor homologado) para decidir a próxima etapa.",
        "quem_usa": "Time de compras e gerência.",
        "tecnica_porque": "O raciocínio fica em uma tag e o resultado em outra. A decisão exige conta (quantidade × valor, em dólar ou euro, contra um limite em reais) e precedência entre regras.",
        "aprendi_projeto": "O gabarito do P5 inclui o limite exato (R$ 5.000,00 não escala) e a conversão de moeda, porque são os pontos em que a conta pode errar. (dados/biblioteca/REVISAO_E_LIMITACOES.md)",
    },
}

EXPERIMENTOS = {
    "E1": {
        "titulo": "Qual técnica usar na extração?",
        "pergunta": "Para extrair os dados de um pedido de compra, vale usar exemplos, raciocínio passo a passo ou um system prompt?",
        "como_medido": "Os 8 campos iguais ao gabarito, que foi escrito e congelado antes de rodar. Média de 3 repetições sobre 50 pedidos fictícios.",
        "ressalva": "Só 4 dos 50 casos separam as técnicas, e o gabarito desses 4 casos é uma decisão minha (calcular o valor unitário a partir do total). É um indício sobre como cada prompt trata um dado implícito, não uma medida geral de qualidade.",
    },
    "E2": {
        "titulo": "Antes e depois de um prompt",
        "pergunta": "Se um prompt erra sempre no mesmo tipo de caso, dá para corrigir com uma regra escrita, sem estragar o resto?",
        "como_medido": "O mesmo prompt (T4) em duas versões, nos mesmos 50 pedidos, 3 repetições cada. A regressão é conferida caso a caso.",
        "ressalva": "A regra nova foi escrita depois de ver os erros nesses mesmos 50 casos. É resultado de desenvolvimento: mostra o ciclo medir, diagnosticar, corrigir e medir de novo, mas não prova que a regra vale para casos novos (isso ainda não foi testado).",
    },
    "E3": {
        "titulo": "Few-shot ajuda na classificação?",
        "pergunta": "Para classificar solicitações de suporte, exemplos com casos ambíguos acertam mais do que só as definições?",
        "o_que_testei": "O P2 sem exemplos (zero-shot) contra o P2 com 6 exemplos (few-shot), nos mesmos 20 casos, 3 repetições cada.",
        "como_medido": "Categoria e urgência iguais ao gabarito (as duas, no mesmo caso). Média de 3 repetições sobre 20 casos fictícios.",
        "ressalva": "Os exemplos cobrem as mesmas famílias de ambiguidade de 6 dos 8 casos de borda: mede se o modelo aprende uma convenção a partir de exemplos, não se generaliza para famílias novas.",
    },
    "E4": {
        "titulo": "Encadear ou pedir tudo de uma vez?",
        "pergunta": "Para pedir ao solicitante os campos que faltam, é melhor extrair e escrever em dois prompts encadeados ou em um só?",
        "o_que_testei": "Fluxo P1 → P3 (dois prompts, o segundo recebe a saída real do primeiro) contra um prompt único que extrai e já escreve o e-mail, nos mesmos 20 pedidos, 3 repetições cada.",
        "como_medido": "O e-mail cita todos os campos que faltam e nenhum que não falta (conferido por regra em código, pelo nome exato do campo). Tom e qualidade do texto não entram no acerto. O custo do fluxo soma as duas chamadas.",
        "ressalva": "O acerto mede os campos citados, não a qualidade do e-mail. No fluxo, um erro de extração do P1 passa para o e-mail.",
    },
    "E5": {
        "titulo": "Vale pagar pelo raciocínio?",
        "pergunta": "Para decidir a próxima etapa de um pedido (aprovar, pedir informação ou escalar), pedir ao modelo que raciocine antes de responder compensa?",
        "o_que_testei": "O P5 com chain-of-thought (raciocínio separado da saída) contra o P5 que responde direto, com a mesma política, nos mesmos 20 casos, 3 repetições cada.",
        "como_medido": "A decisão é igual ao gabarito, que é calculado pela própria política escrita no prompt. Com raciocínio, só o bloco <json> é lido.",
        "ressalva": "A política tem 4 regras e o gabarito segue a política: mede obediência a uma regra escrita, não julgamento. Todas as variantes podem raciocinar internamente (esforço fixado em baixo), o que reduz a diferença.",
    },
}

COMANDOS = {
    "piloto": "python src/rodar_biblioteca.py --piloto",
    "completo": "python src/rodar_biblioteca.py --completo",
    "depois": "python src/analisar_biblioteca.py && python src/consolidar.py && python src/gerar_demo.py && python src/gerar_docs.py",
}

LIMITACOES = [
    "Dados 100% fictícios e gerados por script: mais regulares do que e-mails e chamados reais.",
    "Um único modelo (claude-haiku-5-5), com esforço de raciocínio fixado em baixo; ele não aceita temperatura 0.",
    "O gabarito foi escrito pelo autor do projeto, sem segunda pessoa conferindo; nos casos ambíguos ele reflete convenções minhas.",
    "Poucos casos: 50 na extração e 20 em cada prompt novo. Diferenças de poucos casos são indício, não prova.",
    "A regra do T4 v2 foi escrita olhando os mesmos casos em que foi medida (resultado de desenvolvimento).",
    "A comparação entre as técnicas do E1 usou prompts v1; o T4 v2 foi o único ajustado, então a comparação entre ele e as outras não é simétrica.",
]

NAO_FEITO_ESTADO = {
    "medido": "medido",
    "parcial": "rodada incompleta",
    "nao_medido": "não medido",
}
