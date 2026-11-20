# Preparação para entrevista: perguntas difíceis sobre o projeto

Gerado por `src/gerar_demo.py` a partir de `src/conteudo_demo.py`. A mesma lista aparece na aba "Limites e perguntas" da demo.

## 1. Esses resultados provam que uma técnica é melhor que as outras?

**Estado:** Declarado

**Resposta honesta:** Não. Na rodada v1, todas as respostas erradas vieram de um defeito do gerador de casos (o ponto final de "Ltda." copiado pelo modelo), não de falta de compreensão da tarefa (a contagem de erros difere entre técnicas, mas na recontagem pós-hoc, sem o ponto, elas empatam). Na rodada v2, todo o erro está num único tipo de caso (valor_total), cuja regra de rotulagem é minha e não está escrita nos prompts. O que se pode afirmar é só o que a aba Resultados mostra: quais pares de técnicas têm intervalos de 95% sem sobreposição, sempre com essa ressalva.

**O que mudar:** Repetir a rodada com os prompts atualizados (próxima pergunta).

## 2. O erro do valor_total é falha do modelo?

**Estado:** Não feito

**Resposta honesta:** Não necessariamente. O texto traz só o valor total; o gabarito, escrito por mim, exige dividir pela quantidade. Devolver null é uma leitura defensável de "se a informação não está no texto, use null", regra que o T4 contém. Fatos verificados: os 3 exemplos do T2 sempre trazem o preço unitário pronto, e nenhum prompt menciona a conta. Que isso CAUSOU o erro é hipótese, não foi testado.

**O que mudar:** Criar a versão 2 dos prompts com a regra escrita ("se só houver o total, divida pela quantidade") e rodar de novo. Se o erro some, isso demonstra o ciclo completo de engenharia de prompt: medir, achar a causa, corrigir, medir outra vez.

## 3. Você desenhou a v2 depois de ver a v1. Isso não enviesa o resultado?

**Estado:** Declarado

**Resposta honesta:** Enviesa, e por isso está declarado. A v2 foi criada para corrigir o defeito observado e incluir tipos mais difíceis. A v1 continua como resultado oficial da primeira rodada, e a v2 é uma segunda rodada, nunca uma substituição.

**O que mudar:** Registrar por escrito, antes de rodar, os tipos de caso e as regras de rotulagem (pré-registro) e separar casos de ajuste dos casos de teste.

## 4. Como o intervalo de confiança foi calculado? As repetições são independentes?

**Estado:** Feito, com limite

**Resposta honesta:** Bootstrap percentil: 10.000 reamostragens dos 50 casos, com reposição (seed 42). O valor de cada caso é a média das 3 repetições, então as repetições não são tratadas como casos independentes. Com só 50 casos, os intervalos são largos.

**O que mudar:** Mais casos reduziriam a largura dos intervalos.

## 5. Por que não usou temperatura 0? Dá para reproduzir?

**Estado:** Declarado

**Resposta honesta:** O modelo claude-haiku-5-5 não aceita o parâmetro de temperatura (a API devolveu erro no piloto). A resposta pode variar de uma chamada para outra; medi essa variação com 3 repetições por caso e mostro o mínimo e o máximo. Os números não são reproduzíveis ao dígito. Fixei o esforço de raciocínio em "low" para todas as chamadas.

**O que mudar:** Repetir a rodada completa em outro dia e comparar os intervalos.

## 6. O T4 mede o efeito do system prompt ou das regras que você escreveu nele?

**Estado:** Não feito

**Resposta honesta:** Mistura os dois. O T4 muda o lugar da instrução (system) e também acrescenta regras detalhadas que o T1 não tem. A diferença entre T1 e T4 não isola o efeito do system prompt.

**O que mudar:** Ablação: rodar o T1 com as mesmas regras do T4 escritas na mensagem do usuário, e comparar com o T4.

## 7. Chain-of-thought custou mais. Qual foi o ganho real?

**Estado:** Não feito

**Resposta honesta:** O T3 gasta mais tokens de saída e demora mais (ver a tabela de diferenças). Mas o modelo usa raciocínio interno por padrão, mesmo quando o prompt não pede, então o T3 não é comparado com "nenhum raciocínio". Não dá para atribuir o resultado do T3 ao chain-of-thought em si.

**O que mudar:** Repetir com o raciocínio interno desligado, se o modelo permitir, para isolar o efeito.

## 8. Por que não usou saída estruturada (schema imposto pela API)?

**Estado:** Não feito

**Resposta honesta:** Não testei. É o caminho comum em produção para garantir JSON válido. Aqui o JSON válido ficou em 100% em todas as técnicas, nas duas rodadas, então o formato não foi o gargalo; o gargalo foi a interpretação de casos específicos.

**O que mudar:** Acrescentar uma variante com saída estruturada como quinta técnica.

## 9. Um programa de regras (regex) não resolveria isso sem IA?

**Estado:** Não feito

**Resposta honesta:** Possivelmente, para estes textos, que seguem modelos de frase. Não medi. Sem esse ponto de comparação, não sei se o modelo de linguagem era necessário nesta tarefa.

**O que mudar:** Escrever uma extração por regras como linha de base e comparar acerto e custo.

## 10. Os dados representam o mundo real?

**Estado:** Declarado

**Resposta honesta:** Não. Os textos são gerados por script a partir de modelos de frase (seed 42), em português, com empresa fictícia. O gabarito foi escrito por mim, sem segundo anotador. O resultado não se generaliza para e-mails reais.

**O que mudar:** Usar textos reais anonimizados e um segundo anotador para o gabarito.

## 11. O que se pode concluir por tipo de caso?

**Estado:** Declarado

**Resposta honesta:** Pouco. Cada tipo tem poucos casos (o número aparece entre parênteses no mapa de acerto), então uma porcentagem por tipo é pista, não prova. O mapa mostra também a contagem de respostas certas para isso ficar visível.

**O que mudar:** Aumentar o número de casos nos tipos que interessam.

## 12. O custo é confiável?

**Estado:** Feito, com limite

**Resposta honesta:** É o total de tokens informado pela API multiplicado pelo preço de tabela, consultado na página oficial em 2026-11-19. Não considera descontos por cache nem por processamento em lote. O total gasto no projeto está no README.

**O que mudar:** Registrar nova consulta de preço a cada rodada.

## 13. Posso auditar as respostas brutas?

**Estado:** Não feito

**Resposta honesta:** Parcialmente. O repositório tem prompts, dados, gabaritos, testes, relatórios e resumos. As respostas brutas das 1.200 chamadas ficam fora do Git (regra do .gitignore) e existem só na minha máquina.

**O que mudar:** Publicar as respostas num único arquivo (dados fictícios, sem chave) para qualquer pessoa recalcular os números.

## 14. Que decisão você tomaria com isto?

**Estado:** Hipótese

**Resposta honesta:** Interpretação minha, não resultado medido: começar pela técnica mais barata, escrever explicitamente as regras de negócio que ela não conhece (como a conta do valor total) e medir de novo antes de pagar por técnicas mais caras. A comparação de custo está na aba Resultados.

**O que mudar:** Validar essa decisão com a rodada de prompts v2.

## O que eu mudaria, em ordem

1. **Prompts v2 com a regra do valor total escrita.** É barato, ataca o único erro restante e mostra o ciclo medir, corrigir, medir.
2. **Ablação do system prompt (T1 com as regras de T4 na mensagem do usuário).** Separa o efeito do lugar da instrução do efeito do conteúdo das regras.
3. **Linha de base por regras (regex).** Mostra se o modelo de linguagem era necessário nesta tarefa.
4. **Publicar as respostas brutas em um arquivo.** Permite que qualquer pessoa recalcule os números.
5. **Mais casos e textos menos padronizados.** Reduz o intervalo de confiança e aproxima do uso real.
6. **Saída estruturada como quinta técnica.** Compara com o que se faz em produção para garantir o formato.
