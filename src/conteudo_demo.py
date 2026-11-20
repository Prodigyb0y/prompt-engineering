"""Textos fixos da demo: perguntas difíceis de entrevista, prioridades de mudança e glossário.

Tudo aqui é redação do autor sobre fatos já registrados no repositório. Nenhum número novo:
quando uma resposta cita número, ela manda ver a tabela ou o README.
"""

# (pergunta, resposta honesta, o que mudar, estado)
QA = [
    ("Esses resultados provam que uma técnica é melhor que as outras?",
     "Não. Na rodada v1, todas as respostas erradas vieram de um defeito do gerador de casos (o ponto final de \"Ltda.\" copiado pelo modelo), "
     "não de falta de compreensão da tarefa (a contagem de erros difere entre técnicas, mas na recontagem pós-hoc, sem o ponto, elas empatam). Na rodada v2, todo o erro está num único tipo de caso (valor_total), cuja regra de rotulagem é minha e "
     "não está escrita nos prompts. Em nenhuma das duas rodadas algum par de técnicas atende ao critério de diferença "
     "(intervalos de 95% sem sobreposição e teste do sinal exato pareado com p < 0,05); a seção Resultados traz a tabela de comparações.",
     "Repetir a rodada com os prompts atualizados (próxima pergunta) e com mais casos que separem as técnicas.", "Declarado"),
    ("Você declarou, em algum momento, uma diferença que não se sustenta?",
     "Sim, e foi corrigido. A primeira versão do relatório da v2 dizia que o T3 ficava acima de T2 e T4 porque os intervalos de 95% não se sobrepunham. "
     "O motivo era um artefato: o bootstrap devolve intervalo de 100% a 100% (largura zero) quando a técnica acerta todos os casos. A auditoria de 2026-11-20 "
     "aplicou o teste do sinal exato pareado por caso: T3 melhor em 4 casos, pior em nenhum, p = 0,125 contra T2 e contra T4. O critério passou a exigir os dois "
     "requisitos e a declaração foi retirada. A correção está registrada no README.",
     "Manter os dois requisitos e aumentar o número de casos que separam as técnicas.", "Feito"),
    ("O erro do valor_total é falha do modelo?",
     "Não necessariamente. O texto traz só o valor total; o gabarito, escrito por mim, exige dividir pela quantidade. Devolver null é uma leitura "
     "defensável de \"se a informação não está no texto, use null\", regra que o T4 contém. Fatos verificados: os 3 exemplos do T2 sempre trazem o "
     "preço unitário pronto, e nenhum prompt menciona a conta. Que isso CAUSOU o erro é hipótese, não foi testado.",
     "Criar a versão 2 dos prompts com a regra escrita (\"se só houver o total, divida pela quantidade\") e rodar de novo. Se o erro some, "
     "isso demonstra o ciclo completo de engenharia de prompt: medir, achar a causa, corrigir, medir outra vez.", "Não feito"),
    ("Você desenhou a v2 depois de ver a v1. Isso não enviesa o resultado?",
     "Enviesa, e por isso está declarado. A v2 foi criada para corrigir o defeito observado e incluir tipos mais difíceis. A v1 continua como "
     "resultado oficial da primeira rodada, e a v2 é uma segunda rodada, nunca uma substituição.",
     "Registrar por escrito, antes de rodar, os tipos de caso e as regras de rotulagem (pré-registro) e separar casos de ajuste dos casos de teste.",
     "Declarado"),
    ("Como o intervalo de confiança foi calculado? As repetições são independentes?",
     "Bootstrap percentil: 10.000 reamostragens dos 50 casos, com reposição (seed 42). O valor de cada caso é a média das 3 repetições, então as "
     "repetições não são tratadas como casos independentes. Com só 50 casos, os intervalos são largos, e para uma técnica que acerta 100% o bootstrap "
     "devolve largura zero, que não significa certeza. Por isso a comparação entre técnicas também exige o teste do sinal exato pareado.",
     "Mais casos reduziriam a largura dos intervalos; para acerto de 100%, usar um intervalo exato (Clopper-Pearson) como complemento.", "Feito, com limite"),
    ("Os exemplos do few-shot e os casos de teste são independentes?",
     "Não totalmente. Nenhum texto de teste é igual aos dos exemplos, mas parte dos casos tem o mesmo item ou o mesmo fornecedor de algum exemplo "
     "(a contagem está em AUDITORIA.md da rodada). Isso pode favorecer o T2.",
     "Gerar exemplos com itens e fornecedores que não aparecem nos casos de teste.", "Não feito"),
    ("Quantos casos de fato separam as técnicas?",
     "Poucos. Em cada rodada, quase todos os 50 casos são acertados por todas as técnicas nas 3 repetições; só 4 a 5 casos separam as técnicas, e todos "
     "pertencem a um único tipo (um defeito do gerador na v1, o valor_total na v2). O teste tem baixo poder de discriminação. A contagem está em AUDITORIA.md.",
     "Criar casos mais difíceis e mais variados, com vários tipos que separem as técnicas, congelados antes de rodar.", "Declarado"),
    ("Por que não usou temperatura 0? Dá para reproduzir?",
     "O modelo claude-haiku-5-5 não aceita o parâmetro de temperatura (a API devolveu erro no piloto). A resposta pode variar de uma chamada para outra; "
     "medi essa variação com 3 repetições por caso e mostro o mínimo e o máximo. Os números não são reproduzíveis ao dígito. Fixei o esforço de raciocínio "
     "em \"low\" para todas as chamadas.",
     "Repetir a rodada completa em outro dia e comparar os intervalos.", "Declarado"),
    ("O T4 mede o efeito do system prompt ou das regras que você escreveu nele?",
     "Mistura os dois. O T4 muda o lugar da instrução (system) e também acrescenta regras detalhadas que o T1 não tem. A diferença entre T1 e T4 "
     "não isola o efeito do system prompt.",
     "Ablação: rodar o T1 com as mesmas regras do T4 escritas na mensagem do usuário, e comparar com o T4.", "Não feito"),
    ("Chain-of-thought custou mais. Qual foi o ganho real?",
     "O T3 gasta mais tokens de saída e demora mais (ver a tabela de diferenças). Mas o modelo usa raciocínio interno por padrão, mesmo quando o prompt "
     "não pede, então o T3 não é comparado com \"nenhum raciocínio\". Não dá para atribuir o resultado do T3 ao chain-of-thought em si.",
     "Repetir com o raciocínio interno desligado, se o modelo permitir, para isolar o efeito.", "Não feito"),
    ("Por que não usou saída estruturada (schema imposto pela API)?",
     "Não testei. É o caminho comum em produção para garantir JSON válido. Aqui o JSON válido ficou em 100% em todas as técnicas, nas duas rodadas, "
     "então o formato não foi o gargalo; o gargalo foi a interpretação de casos específicos.",
     "Acrescentar uma variante com saída estruturada como quinta técnica.", "Não feito"),
    ("Um programa de regras (regex) não resolveria isso sem IA?",
     "Possivelmente, para estes textos, que seguem modelos de frase. Não medi. Sem esse ponto de comparação, não sei se o modelo de linguagem era "
     "necessário nesta tarefa.",
     "Escrever uma extração por regras como linha de base e comparar acerto e custo.", "Não feito"),
    ("Os dados representam o mundo real?",
     "Não. Os textos são gerados por script a partir de modelos de frase (seed 42), em português, com empresa fictícia. O gabarito foi escrito por mim, "
     "sem segundo anotador. O resultado não se generaliza para e-mails reais.",
     "Usar textos reais anonimizados e um segundo anotador para o gabarito.", "Declarado"),
    ("O que se pode concluir por tipo de caso?",
     "Pouco. Cada tipo tem poucos casos (o número aparece entre parênteses no mapa de acerto), então uma porcentagem por tipo é pista, não prova. "
     "O mapa mostra também a contagem de respostas certas para isso ficar visível.",
     "Aumentar o número de casos nos tipos que interessam.", "Declarado"),
    ("O custo é confiável?",
     "É o total de tokens informado pela API multiplicado pelo preço de tabela, consultado na página oficial em 2026-11-19. Não considera descontos "
     "por cache nem por processamento em lote. O total gasto no projeto está no README.",
     "Registrar nova consulta de preço a cada rodada.", "Feito, com limite"),
    ("Posso auditar as respostas brutas?",
     "Parcialmente. O repositório tem prompts, dados, gabaritos, testes, relatórios e resumos. As respostas brutas das 1.200 chamadas ficam fora do Git "
     "(regra do .gitignore) e existem só na minha máquina.",
     "Publicar as respostas num único arquivo (dados fictícios, sem chave) para qualquer pessoa recalcular os números.", "Não feito"),
    ("Que decisão você tomaria com isto?",
     "Interpretação minha, não resultado medido: começar pela técnica mais barata, escrever explicitamente as regras de negócio que ela não conhece "
     "(como a conta do valor total) e medir de novo antes de pagar por técnicas mais caras. A comparação de custo está na seção Resultados.",
     "Validar essa decisão com a rodada de prompts v2.", "Hipótese"),
]

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
