"""Textos fixos da demo: perguntas difíceis de entrevista, prioridades de mudança e glossário.

Tudo aqui é redação do autor sobre fatos já registrados no repositório. Nenhum número novo:
quando uma resposta cita número, ela manda ver a tabela ou o README.
"""

# (pergunta, resposta honesta, o que mudar, estado)
QA = [
    ("Esses resultados provam que uma técnica é melhor que as outras?",
     "Não. Na rodada v1, todas as respostas erradas vieram de um defeito do gerador de casos (o ponto final de \"Ltda.\" copiado pelo modelo), "
     "não de falta de compreensão da tarefa (a contagem de erros difere entre técnicas, mas na recontagem pós-hoc, sem o ponto, elas empatam). Na rodada v2, todo o erro está num único tipo de caso (valor_total), cuja regra de rotulagem é minha e "
     "não está escrita nos prompts. O que se pode afirmar é só o que a aba Resultados mostra: quais pares de técnicas têm intervalos de 95% "
     "sem sobreposição, sempre com essa ressalva.",
     "Repetir a rodada com os prompts atualizados (próxima pergunta).", "Declarado"),
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
     "repetições não são tratadas como casos independentes. Com só 50 casos, os intervalos são largos.",
     "Mais casos reduziriam a largura dos intervalos.", "Feito, com limite"),
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
     "(como a conta do valor total) e medir de novo antes de pagar por técnicas mais caras. A comparação de custo está na aba Resultados.",
     "Validar essa decisão com a rodada de prompts v2.", "Hipótese"),
]

# ordem sugerida de mudanças: (título, por quê)
PRIORIDADES = [
    ("Prompts v2 com a regra do valor total escrita", "É barato, ataca o único erro restante e mostra o ciclo medir, corrigir, medir."),
    ("Ablação do system prompt (T1 com as regras de T4 na mensagem do usuário)", "Separa o efeito do lugar da instrução do efeito do conteúdo das regras."),
    ("Linha de base por regras (regex)", "Mostra se o modelo de linguagem era necessário nesta tarefa."),
    ("Publicar as respostas brutas em um arquivo", "Permite que qualquer pessoa recalcule os números."),
    ("Mais casos e textos menos padronizados", "Reduz o intervalo de confiança e aproxima do uso real."),
    ("Saída estruturada como quinta técnica", "Compara com o que se faz em produção para garantir o formato."),
]

# (seção, [(termo, definição)])
GLOSSARIO = [
    ("Siglas desta página", [
        ("T1 · zero-shot (\"pedir direto\")", "O prompt traz só a instrução e a lista de campos. \"Shot\" quer dizer exemplo; zero-shot é sem nenhum exemplo."),
        ("T2 · few-shot (\"mostrar exemplos\")", "O prompt traz alguns exemplos já resolvidos (aqui, 3) antes do caso real."),
        ("T3 · chain-of-thought (\"pensar em voz alta\")", "O prompt pede que o modelo escreva o raciocínio antes da resposta final. Só o JSON final é lido."),
        ("T4 · system prompt (\"papel e regras\")", "Papel, regras e formato ficam no system prompt, a parte da instrução que vale para toda a conversa."),
        ("Dados v1 e v2", "Dois conjuntos de 50 casos. A v2 foi criada depois de ver o resultado da v1, para corrigir um defeito e testar tipos mais difíceis."),
        ("Prompt v1 e hash", "Cada texto de prompt tem versão e um código de 12 caracteres (hash SHA-256). Se o texto mudar, o código muda."),
    ]),
    ("Conceitos", [
        ("Prompt", "A instrução escrita que se dá ao modelo de IA."),
        ("Modelo", "O sistema de IA que responde. Aqui, sempre o claude-haiku-5-5."),
        ("JSON", "Formato de texto para dados organizados, com nome do campo e valor, que um programa consegue ler."),
        ("Schema", "O molde do JSON: quais campos existem, de que tipo e quais valores são permitidos."),
        ("Campo", "Cada informação a extrair. Aqui são 8: solicitante_area, item, quantidade, unidade, prazo_entrega, valor_unitario, moeda e fornecedor."),
        ("null", "Valor que significa \"não há informação\". É a resposta certa quando o texto não traz o dado."),
        ("Token", "Pedaço de texto que o modelo lê e escreve, geralmente uma palavra ou parte dela. A API cobra por token."),
        ("Temperatura", "Parâmetro que controla o grau de aleatoriedade das respostas. Este modelo não aceita esse parâmetro, então as respostas podem variar."),
        ("Esforço de raciocínio (effort)", "Parâmetro que indica quanto o modelo pode \"pensar\" antes de responder. Foi fixado em baixo em todas as chamadas."),
    ]),
    ("Dados e medição", [
        ("Caso", "Um texto de pedido de compra fictício. São 50 por rodada."),
        ("Tipo de caso", "A situação que o caso testa, por exemplo valor em formato brasileiro ou prazo relativo."),
        ("Gabarito", "A resposta certa de cada caso, escrita antes de rodar e congelada. Congelar significa registrar o hash do arquivo; mudar depois obriga a registrar e rodar tudo de novo."),
        ("Normalização", "Regra aplicada antes de comparar: remover acentos, ignorar maiúsculas e espaços extras. Números e datas precisam bater exatamente."),
        ("Repetição", "Cada caso é enviado 3 vezes por técnica, porque a resposta do modelo pode variar."),
        ("Acerto por campo", "Percentual de campos que bateram com o gabarito."),
        ("Acerto por caso", "Um caso só conta como certo se os 8 campos baterem. É a medida principal desta página."),
        ("JSON válido e schema válido", "JSON válido: o texto pode ser lido como JSON. Schema válido: além disso, tem exatamente os campos e valores permitidos."),
        ("Intervalo de confiança de 95% (IC)", "Faixa em que o acerto verdadeiro provavelmente está. Se as faixas de duas técnicas se sobrepõem, não se declara qual é melhor."),
        ("Bootstrap", "Método para obter o IC: sorteia 50 casos com reposição, 10.000 vezes, calcula o acerto de cada sorteio e usa a faixa que cobre 95% deles."),
        ("Mín–máx entre repetições", "O menor e o maior acerto entre as 3 repetições, para mostrar a variação."),
        ("Oficial e pós-hoc", "Oficial: regra definida antes de medir. Pós-hoc: recontagem feita depois de ver os resultados, sempre marcada como não oficial."),
        ("Artefato", "Defeito que vem do método e não do que se queria medir. Exemplo: o ponto final de \"Ltda.\" nos textos da v1."),
        ("Seed", "Número fixo que faz o sorteio ser repetível. Aqui, 42."),
    ]),
    ("Custo e velocidade", [
        ("Custo por caso", "Tokens de entrada e saída informados pela API, multiplicados pelo preço de tabela, divididos pelo número de respostas."),
        ("Custo por acerto", "Gasto total da técnica dividido pelo número de respostas certas."),
        ("Latência", "Tempo de uma chamada, do envio até a resposta completa, medido com time.perf_counter."),
        ("Teto de gasto", "Limite de US$ 1,00 no projeto inteiro. O código reserva o custo máximo antes de cada chamada e para antes de passar do limite."),
    ]),
]
