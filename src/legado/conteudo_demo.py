"""Textos fixos da demo: anatomia do prompt, métricas, limitações e próximos passos.

Tudo aqui é redação do autor sobre fatos já registrados no repositório. Nenhum número novo:
quando uma resposta cita número, ela manda ver a tabela ou o README.
"""

# ordem sugerida de mudanças: (título, por quê)
PRIORIDADES = [
    ("Validar o T4 v2 em casos novos, escritos e congelados antes de rodar", "A regra nova foi escrita depois de ver os erros nos 50 casos v2; só casos que ela nunca viu mostram se generaliza."),
    ("Fazer a mesma iteração no T2, acrescentando um exemplo em que o total vira valor unitário", "Compara duas formas de corrigir o mesmo erro: regra escrita contra exemplo."),
    ("Ablação do system prompt: T1 com as regras do T4 na mensagem do usuário", "Separa o efeito do lugar da instrução do efeito do conteúdo das regras."),
    ("Exemplos do few-shot sem itens nem fornecedores dos casos de teste", "Remove a sobreposição que pode favorecer o T2."),
    ("Mais casos e textos menos padronizados", "Aumenta o número de casos que separam as técnicas."),
]

# anatomia do prompt T4: (nome da parte, função); a ordem segue o texto do prompt (papel, campos, 8 regras)
ANATOMIA = [
    ("Papel e tarefa", "Define quem responde e limita o escopo a uma única tarefa."),
    ("Contrato de saída (campos)", "Fixa nomes, tipos e valores permitidos. É o que permite validar a resposta por programa."),
    ("Regra · formato da resposta", "Exige só o JSON, sem texto antes ou depois, para que a saída seja lida direto por um sistema."),
    ("Regra · dado ausente", "Diz o que fazer quando falta informação (null) e proíbe inventar. Tipo de caso: informação faltando."),
    ("Regra · quantidade", "Desambigua quando há dois números no texto. Tipo de caso: duas quantidades."),
    ("Regra · valor numérico", "Normaliza o formato brasileiro (\"R$ 1.200,00\" vira 1200). Tipo de caso: valor em formato brasileiro."),
    ("Regra · moeda", "Converte o símbolo no código da moeda. Tipo de caso: moeda por símbolo."),
    ("Regra · prazo", "Só aceita data completa e manda prazo relativo para null. Tipos: datas em formatos variados e prazo relativo."),
    ("Regra · fornecedor", "Pede cópia literal do nome, inclusive apelido. Tipo de caso: fornecedor por apelido."),
    ("Regra · ruído", "Manda ignorar saudação, assinatura e erro de digitação. Tipo de caso: ruído."),
]
ANATOMIA_NOTA = ("Cada regra corresponde a um tipo de caso do teste. Nenhuma regra cobre o caso em que o texto traz só o valor total; esse tipo entrou nos dados v2 "
                 "e concentrou todos os erros da rodada v2.")

# métrica, definição, como foi medida
METRICAS = [
    ("Acerto por caso", "Fração das respostas em que os 8 campos são iguais ao gabarito.",
     "Comparação campo a campo após normalização (sem acento, minúsculas, espaços colapsados); números e datas exatos; null só é igual a null. Média das 3 repetições de cada caso."),
    ("Intervalo de confiança de 95%", "Faixa em que o acerto verdadeiro provavelmente se encontra.",
     "Bootstrap percentil: 10.000 reamostragens dos 50 casos com reposição (seed 42). O valor de cada caso é a média das 3 repetições."),
    ("Comparação entre técnicas", "Critério para declarar que uma técnica é melhor que outra.",
     "Intervalos de 95% sem sobreposição e teste do sinal exato pareado por caso (bilateral, empates excluídos) com p < 0,05. O bootstrap sozinho não basta: "
     "ele devolve intervalo de 100% a 100% quando a técnica acerta todos os casos."),
    ("Mín–máx entre repetições", "Variação do acerto entre execuções.", "O acerto por caso é calculado sobre os 50 casos em cada repetição, separadamente; a tabela mostra o menor e o maior dos 3 valores."),
    ("JSON válido", "A resposta pode ser lida como JSON e respeita o schema.", "json.loads e modelo pydantic estrito, com campos extras proibidos (extra=\"forbid\")."),
    ("Custo por caso", "Gasto médio por resposta, em dólares.", "Tokens de entrada e de saída informados pela API multiplicados pelo preço de tabela do modelo (página oficial, consulta em 2026-11-19), dividido pelo número de respostas."),
    ("Custo por acerto", "Gasto da técnica dividido pelas respostas certas.", "Custo total da técnica ÷ número de respostas com caso correto."),
    ("Latência", "Tempo de cada chamada à API.", "time.perf_counter antes e depois da chamada; a tabela traz a média."),
    ("Tokens", "Unidade de texto cobrada pela API.", "Contagem informada pela própria API em cada resposta; a tabela traz a média por resposta."),
]

# limitações permanentes (a limitação específica da rodada é acrescentada pelo gerador)
LIMITACOES = [
    "Amostra: 50 casos por rodada e poucos casos por tipo. Os intervalos de confiança são largos e as porcentagens por tipo servem como indício.",
    "Um único modelo (claude-haiku-5-5), com esforço de raciocínio fixado em baixo. O modelo não aceita temperatura 0, então as respostas variam entre execuções; a variação é medida com 3 repetições.",
    "Dados sintéticos, gerados por script a partir de modelos de frase. O gabarito foi escrito pelo próprio autor, sem segundo anotador. O resultado não se generaliza para e-mails reais.",
    "A rodada v2 foi desenhada depois de conhecer o resultado da v1. A v1 permanece como resultado oficial da primeira rodada.",
    "O T4 combina o lugar da instrução (system) com regras detalhadas, e o T3 não isola o chain-of-thought do raciocínio interno do modelo. Nenhum dos dois comparativos isola um único fator.",
    "Não há comparação com um extrator por regras nem com saída estruturada imposta pela API. As respostas brutas não estão versionadas no Git.",
]
