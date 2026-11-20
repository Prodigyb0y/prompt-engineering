"""Biblioteca de prompts do Prompt Lab · Gutenberg Systems (empresa fictícia).

Fonte única: este módulo gera os arquivos de prompts/ (P1 a P5 e os controles dos experimentos).
Cada prompt tem versão, hash (mesma regra de prompts_lib.hash_prompt) e o campo `anatomia`:
trechos do texto do próprio prompt, marcados por parte, que a demo usa para colorir. Um teste
confere que cada trecho existe, literalmente, no prompt (não dá para a anatomia divergir do texto).

Papéis de cada arquivo:
  biblioteca  o prompt que aparece como cartão (P1 a P5)
  controle    a alternativa contra a qual o prompt da biblioteca é comparado em um experimento

Mudou o texto -> o hash muda -> crie nova versão (não edite uma versão já medida).
"""
import json
from pathlib import Path

import prompts_lib as pl

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "prompts"

# Partes da anatomia (ordem e rótulo usados na legenda da demo)
PARTES = {
    "papel": "Papel",
    "contexto": "Contexto",
    "tarefa": "Tarefa",
    "formato_saida": "Formato de saída",
    "regras": "Regras",
    "casos_borda": "Casos de borda",
    "exemplos": "Exemplos",
    "raciocinio": "Raciocínio separado da saída",
}

# ---------------------------------------------------------------------------------------------
# P1 - extrair pedido de compra (é o T4 v2 já medido; texto idêntico, hash idêntico)
# ---------------------------------------------------------------------------------------------
P1_SYSTEM = pl.T4_SYSTEM_V2
P1_USER = pl.T4_USER
P1_ANATOMIA = [
    ("papel", "Você é um assistente de extração de dados", "Define quem responde: um extrator, não um conversador."),
    ("contexto", "do setor de compras da Gutenberg Systems, empresa fictícia.", "Situa o modelo no negócio; ajuda a interpretar abreviações e apelidos de fornecedor."),
    ("tarefa", "Sua única tarefa é ler uma solicitação de compra em texto livre e devolver um objeto JSON.", "Uma tarefa só, dita de forma direta. O \"única\" corta respostas com conversa."),
    ("formato_saida", pl.SCHEMA, "Os 8 campos, com tipo e valores permitidos. Sem isso o JSON sairia diferente a cada chamada."),
    ("regras", "- Responda somente com o objeto JSON, sem explicações e sem formatação extra.", "Torna a saída legível por código, sem limpeza."),
    ("regras", "- Se uma informação não estiver no texto, use null. Não invente valores.", "Evita invenção: campo ausente vira null, não um palpite."),
    ("casos_borda", "- quantidade é a quantidade do item pedido; ignore outras quantidades citadas no texto (estoque, pedidos anteriores).", "Caso de borda: duas quantidades no mesmo texto."),
    ("casos_borda", "- Se o texto trouxer só o valor total, e não o valor unitário, divida o total pela quantidade para obter valor_unitario. A moeda é a do total.", "As duas linhas da iteração v1 → v2: a regra de negócio que faltava (ver Experimento 2)."),
    ("casos_borda", "Prazos relativos (\"daqui 15 dias\", \"semana que vem\") viram null.", "Caso de borda: data que não é data."),
]

# ---------------------------------------------------------------------------------------------
# P2 - classificar solicitação de suporte interno (técnica: few-shot com casos ambíguos)
# ---------------------------------------------------------------------------------------------
P2_DEFINICOES = """Categorias (escolha uma):
- acesso: login, senha, permissão, conta bloqueada, novo usuário
- equipamento: computador, monitor, impressora, headset, celular corporativo, defeito físico
- software: programa, sistema interno ou licença com erro, instalação ou atualização
- rede: internet, wi-fi, VPN, link, servidor ou site fora do ar
- instalacoes: ar-condicionado, iluminação, mobiliário, limpeza, porta, estacionamento
- folha_beneficios: holerite, ponto, férias, vale-refeição, plano de saúde

Urgência (escolha uma):
- critica: para uma área inteira ou envolve segurança de pessoas ou de dados
- alta: impede uma pessoa de trabalhar e não há alternativa
- media: atrapalha, mas existe um jeito de contornar
- baixa: pedido sem prazo ou melhoria"""

P2_SAIDA = 'Responda somente com um objeto JSON, sem texto antes ou depois: {"categoria": "...", "urgencia": "..."}'

P2_CABECALHO = "Você classifica solicitações de suporte interno da Gutenberg Systems (empresa fictícia)."

# Exemplos do few-shot: escritos à mão, com os casos ambíguos que o texto das definições não resolve.
# Disjuntos dos casos de teste (conferido em tests/test_biblioteca_dados.py).
EXEMPLOS_P2 = [
    {"entrada": "Não consigo abrir o sistema de estoque. A página nem carrega e a VPN fica caindo. Sem isso não tenho como trabalhar de casa.",
     "saida": {"categoria": "rede", "urgencia": "alta"}},
    {"entrada": "A VPN está funcionando, mas o sistema de contratos diz que não tenho permissão para ver a pasta do meu time. Preciso até amanhã.",
     "saida": {"categoria": "acesso", "urgencia": "media"}},
    {"entrada": "O monitor do meu posto pisca e às vezes apaga, e o sistema de pedidos fecha junto. Dá para trabalhar se eu reiniciar de tempos em tempos.",
     "saida": {"categoria": "equipamento", "urgencia": "media"}},
    {"entrada": "Mandei por engano a senha da minha conta para um número que não conheço. Acho melhor alguém olhar isso agora.",
     "saida": {"categoria": "acesso", "urgencia": "critica"}},
    {"entrada": "n precisa ser agora, mas a cadeira da minha baia range muito kkk quando puderem olhar",
     "saida": {"categoria": "instalacoes", "urgencia": "baixa"}},
    {"entrada": "O vale-refeição ainda não foi creditado este mês. Hoje consigo almoçar por conta própria, mas queria entender.",
     "saida": {"categoria": "folha_beneficios", "urgencia": "media"}},
]


def _bloco_exemplos(exemplos):
    partes = []
    for i, e in enumerate(exemplos, 1):
        partes.append(f"Exemplo {i}\nSolicitação:\n{e['entrada']}\nJSON:\n{json.dumps(e['saida'], ensure_ascii=False)}")
    return "\n\n".join(partes)


P2_ZERO_USER = f"{P2_CABECALHO}\n\n{P2_DEFINICOES}\n\n{P2_SAIDA}\n\nSolicitação:\n{{texto}}\nJSON:"
P2_FEW_USER = (f"{P2_CABECALHO}\n\n{P2_DEFINICOES}\n\n{P2_SAIDA}\n\n"
               f"Os exemplos abaixo mostram como decidir quando a solicitação cabe em mais de uma categoria ou urgência.\n\n"
               f"{_bloco_exemplos(EXEMPLOS_P2)}\n\nAgora a solicitação real\nSolicitação:\n{{texto}}\nJSON:")
P2_ANATOMIA = [
    ("papel", "Você classifica solicitações de suporte interno", "Papel curto: classificador, não atendente."),
    ("contexto", "da Gutenberg Systems (empresa fictícia).", "Contexto mínimo; as definições abaixo carregam o resto."),
    ("tarefa", "Os exemplos abaixo mostram como decidir quando a solicitação cabe em mais de uma categoria ou urgência.", "Diz ao modelo para que servem os exemplos."),
    ("formato_saida", P2_SAIDA, "JSON de duas chaves, sem texto extra."),
    ("regras", P2_DEFINICOES, "Definições de cada categoria e de cada nível de urgência. Não resolvem os empates; por isso há exemplos."),
    ("exemplos", _bloco_exemplos(EXEMPLOS_P2), "Seis exemplos com os empates mais comuns: VPN contra permissão, defeito físico contra software, segurança de dados, pedido sem pressa com ruído."),
]

# ---------------------------------------------------------------------------------------------
# P3 - e-mail pedindo só o que faltou (técnica: prompt encadeado; recebe a saída do P1)
# ---------------------------------------------------------------------------------------------
P3_CAMPOS = [  # campo do P1 -> nome exato usado no e-mail (vocabulário controlado, conferido em código)
    ("solicitante_area", "área solicitante"),
    ("prazo_entrega", "prazo de entrega"),
    ("valor_unitario", "valor unitário"),
    ("fornecedor", "fornecedor"),
]
P3_SENTINELA = "NENHUM_CAMPO_FALTANTE"

P3_CAMPOS_BLOCO = """Campos que podem faltar e o nome exato que você deve usar ao pedi-los:
- solicitante_area vazio: "área solicitante"
- prazo_entrega vazio: "prazo de entrega"
- valor_unitario vazio: "valor unitário" (peça também a moeda)
- fornecedor vazio: "fornecedor"
""".rstrip()

P3_REGRAS_RESTO = f"""Regras do e-mail:
- Peça somente os campos que faltam. Nunca peça nem cite um campo que já veio preenchido.
- Use o nome exato do campo, sem sinônimos.
- Você pode confirmar o item e a quantidade recebidos em uma frase; não peça nada sobre eles.
- Se nenhum campo faltar, responda apenas {P3_SENTINELA}.

Tom: profissional e cordial, frases curtas, trate o solicitante por "você". Sem pedir desculpas, sem tom de cobrança, sem jargão. Termine com um agradecimento breve.

Formato: primeira linha "Assunto: ...", uma linha em branco e o corpo com até 120 palavras. Assine "Equipe de Compras · Gutenberg Systems". Sem markdown."""

P3_REGRAS_EMAIL = P3_CAMPOS_BLOCO + "\n\n" + P3_REGRAS_RESTO

P3_SYSTEM = ("Você escreve e-mails para a equipe de Compras da Gutenberg Systems (empresa fictícia). "
             "Você recebe os dados já extraídos de uma solicitação de compra, em JSON, "
             "e escreve um e-mail curto ao solicitante pedindo apenas as informações que faltam.\n\n" + P3_REGRAS_EMAIL)
P3_USER = "Dados extraídos (JSON):\n{texto}"
P3_ANATOMIA = [
    ("papel", "Você escreve e-mails para a equipe de Compras da Gutenberg Systems (empresa fictícia).", "Papel e empresa."),
    ("contexto", "Você recebe os dados já extraídos de uma solicitação de compra, em JSON,", "Encadeamento: a entrada deste prompt é a saída do P1."),
    ("tarefa", "e escreve um e-mail curto ao solicitante pedindo apenas as informações que faltam.", "A tarefa: pedir só o que falta."),
    ("regras", 'Campos que podem faltar e o nome exato que você deve usar ao pedi-los:\n- solicitante_area vazio: "área solicitante"\n- prazo_entrega vazio: "prazo de entrega"\n- valor_unitario vazio: "valor unitário" (peça também a moeda)\n- fornecedor vazio: "fornecedor"',
     "Vocabulário controlado: cada campo tem um nome fixo, o que permite conferir o e-mail por regra em código."),
    ("regras", "- Peça somente os campos que faltam. Nunca peça nem cite um campo que já veio preenchido.", "A regra central do prompt."),
    ("casos_borda", f"- Se nenhum campo faltar, responda apenas {P3_SENTINELA}.", "Caso de borda: nada a pedir. Devolve um código, não um e-mail inútil."),
    ("regras", 'Tom: profissional e cordial, frases curtas, trate o solicitante por "você". Sem pedir desculpas, sem tom de cobrança, sem jargão. Termine com um agradecimento breve.', "Controle de tom: o tom é escrito, não deixado ao acaso."),
    ("formato_saida", 'Formato: primeira linha "Assunto: ...", uma linha em branco e o corpo com até 120 palavras. Assine "Equipe de Compras · Gutenberg Systems". Sem markdown.', "Formato e tamanho do e-mail."),
]

# Controle do E4: um único prompt que extrai e escreve o e-mail de uma vez
P3U_SYSTEM = ("Você escreve e-mails para a equipe de Compras da Gutenberg Systems (empresa fictícia). "
              "Você recebe a mensagem original de uma solicitação de compra, em texto livre. "
              "Primeiro identifique, sem escrever, quais das informações abaixo NÃO aparecem na mensagem. "
              "Depois escreva um e-mail curto ao solicitante pedindo apenas as que faltam.\n\n"
              "Como decidir se uma informação falta:\n"
              "- área solicitante: falta se a mensagem não diz a área de quem pede.\n"
              "- prazo de entrega: falta se não há uma data completa com dia, mês e ano. Prazos relativos (\"daqui 15 dias\", \"semana que vem\") contam como faltando.\n"
              "- valor unitário: falta se não há nenhum valor. Se houver só o valor total, o valor está informado.\n"
              "- fornecedor: falta se a mensagem não cita fornecedor.\n\n"
              'Nomes exatos que você deve usar ao pedir cada campo: "área solicitante", "prazo de entrega", '
              '"valor unitário" (peça também a moeda) e "fornecedor".\n\n' + P3_REGRAS_RESTO)
P3U_USER = "Mensagem da solicitação:\n{texto}"

# ---------------------------------------------------------------------------------------------
# P4 - resumir reclamação em JSON (técnica: saída estruturada com regras de "não inventar")
# ---------------------------------------------------------------------------------------------
P4_SYSTEM = """Você é um analista de atendimento da Gutenberg Systems (empresa fictícia). Você lê uma reclamação de cliente e devolve um resumo estruturado em JSON.

Campos do JSON (use exatamente estes nomes, sem campos extras):
- resumo: uma frase com até 20 palavras, só com fatos que estão no texto
- motivo: um de "atraso_entrega", "produto_com_defeito", "produto_errado", "cobranca_indevida", "atendimento", "indefinido"
- sentimento: um de "irritado", "insatisfeito", "neutro"
- acao_sugerida: um de "rastrear_pedido", "trocar_produto", "reembolsar", "corrigir_cobranca", "ligar_para_cliente", "pedir_mais_informacao"
- numero_pedido: string no formato PED-12345, ou null
- valor_reclamado: número em reais, ou null

Regras de não inventar:
- numero_pedido e valor_reclamado só recebem valor se aparecerem escritos no texto. Se não aparecerem, use null. Nunca deduza, arredonde nem complete.
- O resumo não pode conter número, data ou nome que não esteja no texto.
- Se o texto não deixa claro o que deu errado, use motivo "indefinido" e acao_sugerida "pedir_mais_informacao".

Regras de decisão:
- sentimento "irritado" quando há xingamento, ameaça, ironia pesada ou texto em maiúsculas; "neutro" quando só descreve o problema sem emoção; nos demais casos, "insatisfeito".
- acao_sugerida: atraso_entrega -> rastrear_pedido; produto_com_defeito ou produto_errado -> trocar_produto; cobranca_indevida -> corrigir_cobranca; atendimento -> ligar_para_cliente.
- Se o cliente pedir o dinheiro de volta, use reembolsar. Se ameaçar acionar Procon ou a Justiça, use ligar_para_cliente, qualquer que seja o motivo.

Responda somente com o objeto JSON, sem explicações e sem formatação extra."""
P4_USER = "Reclamação:\n{texto}"
P4_ANATOMIA = [
    ("papel", "Você é um analista de atendimento da Gutenberg Systems (empresa fictícia).", "Papel e empresa."),
    ("tarefa", "Você lê uma reclamação de cliente e devolve um resumo estruturado em JSON.", "A tarefa, em uma frase."),
    ("formato_saida", "Campos do JSON (use exatamente estes nomes, sem campos extras):\n- resumo: uma frase com até 20 palavras, só com fatos que estão no texto", "Schema fechado: valores permitidos listados, sem campos extras."),
    ("regras", "- numero_pedido e valor_reclamado só recebem valor se aparecerem escritos no texto. Se não aparecerem, use null. Nunca deduza, arredonde nem complete.", "A regra de \"não inventar\": a mais importante deste prompt."),
    ("regras", "- O resumo não pode conter número, data ou nome que não esteja no texto.", "Estende a regra ao texto livre do resumo."),
    ("casos_borda", '- Se o texto não deixa claro o que deu errado, use motivo "indefinido" e acao_sugerida "pedir_mais_informacao".', "Dá ao modelo uma saída honesta quando não há informação."),
    ("regras", "- acao_sugerida: atraso_entrega -> rastrear_pedido; produto_com_defeito ou produto_errado -> trocar_produto; cobranca_indevida -> corrigir_cobranca; atendimento -> ligar_para_cliente.", "Tabela de decisão escrita no prompt: a regra de negócio não fica implícita."),
    ("casos_borda", "- Se o cliente pedir o dinheiro de volta, use reembolsar. Se ameaçar acionar Procon ou a Justiça, use ligar_para_cliente, qualquer que seja o motivo.", "Exceções que mudam a ação."),
]

# ---------------------------------------------------------------------------------------------
# P5 - decidir a próxima etapa (técnica: chain-of-thought com raciocínio separado da saída)
# ---------------------------------------------------------------------------------------------
HOMOLOGADOS = ["Papelaria Aurora Ltda", "Metalúrgica Vale Verde", "Distribuidora Pinheiro", "Informática Bitmais", "Eletrotécnica Faísca"]
CONTROLADOS = ["álcool isopropílico", "óleo lubrificante", "solda em barra"]
LIMITE_BRL = 5000
CAMBIO = {"BRL": 1, "USD": 5, "EUR": 6}

LIMITE_TXT = "5.000,00"

P5_POLITICA = f"""Você decide a próxima etapa de uma solicitação de compra da Gutenberg Systems (empresa fictícia), conforme a política abaixo. A solicitação chega como JSON, com os mesmos campos do P1.

Política:
1. Campos obrigatórios: item, quantidade, unidade, prazo_entrega, valor_unitario, moeda e fornecedor. solicitante_area é opcional. Se algum campo obrigatório for null, a decisão é "pedir_informacao", mesmo que exista outro motivo para escalar.
2. Valor total = quantidade x valor_unitario, convertido para reais: US$ 1 = R$ {CAMBIO['USD']},00 e € 1 = R$ {CAMBIO['EUR']},00.
3. Escalar para a gerência ("escalar") se qualquer uma destas condições for verdadeira:
   a. o valor total em reais for MAIOR que R$ {LIMITE_TXT} (exatamente R$ {LIMITE_TXT} não escala);
   b. o fornecedor não estiver na lista de homologados: {", ".join(HOMOLOGADOS)};
   c. o item for controlado: {", ".join(CONTROLADOS)}.
4. Nos demais casos, "aprovar"."""

P5_SAIDA_DIRETA = 'Responda somente com um objeto JSON, sem texto antes ou depois: {"decisao": "aprovar" | "pedir_informacao" | "escalar", "motivo": "uma frase curta"}'
P5_SAIDA_COT = ("Antes de decidir, raciocine passo a passo dentro de <raciocinio></raciocinio>: confira os campos obrigatórios, "
                "calcule o valor total em reais e verifique fornecedor e item, nessa ordem. "
                'Depois escreva o resultado dentro de <json></json>, só com o objeto {"decisao": "aprovar" | "pedir_informacao" | "escalar", "motivo": "uma frase curta"}, sem mais nada dentro dessa tag.')
P5_USER = "Solicitação (JSON):\n{texto}"
P5_COT_SYSTEM = P5_POLITICA + "\n\n" + P5_SAIDA_COT
P5_DIRETO_SYSTEM = P5_POLITICA + "\n\n" + P5_SAIDA_DIRETA
P5_ANATOMIA = [
    ("papel", "Você decide a próxima etapa de uma solicitação de compra", "Papel: decisor de uma política, não um assistente genérico."),
    ("contexto", "A solicitação chega como JSON, com os mesmos campos do P1.", "Encaixa este prompt no fluxo: a entrada vem da extração."),
    ("regras", "1. Campos obrigatórios: item, quantidade, unidade, prazo_entrega, valor_unitario, moeda e fornecedor.", "A política escrita como regras numeradas e verificáveis."),
    ("casos_borda", 'mesmo que exista outro motivo para escalar.', "Precedência explícita: faltar dado vence qualquer outro motivo."),
    ("casos_borda", f"(exatamente R$ {LIMITE_TXT} não escala)", "Caso de borda no limite: \"maior que\" não inclui o valor exato."),
    ("regras", "2. Valor total = quantidade x valor_unitario, convertido para reais:", "A conta que o modelo precisa fazer antes de comparar com o limite."),
    ("raciocinio", "Antes de decidir, raciocine passo a passo dentro de <raciocinio></raciocinio>:", "Raciocínio em uma tag, resultado em outra: só o <json> é lido pelo sistema."),
    ("formato_saida", 'Depois escreva o resultado dentro de <json></json>, só com o objeto {"decisao": "aprovar" | "pedir_informacao" | "escalar", "motivo": "uma frase curta"}, sem mais nada dentro dessa tag.', "Saída estruturada separada do raciocínio."),
]


def definicoes():
    """Todos os prompts da biblioteca e dos controles. `arquivo` é o nome em prompts/."""
    d = [
        {"id": "P1", "nome": "Extrair pedido de compra em 8 campos", "tecnica": "system_prompt", "versao": "v2", "papel": "biblioteca",
         "descricao_tecnica": "System prompt e saída estruturada", "system": P1_SYSTEM, "user_template": P1_USER, "anatomia": P1_ANATOMIA,
         "origem": "É o T4 v2 já medido (prompts/extracao/T4_system_prompt_v2.json), com o mesmo texto e o mesmo hash."},
        {"id": "P2", "nome": "Classificar solicitação de suporte interno", "tecnica": "few_shot", "versao": "v1", "papel": "biblioteca",
         "descricao_tecnica": "Few-shot com casos ambíguos", "system": "", "user_template": P2_FEW_USER, "anatomia": P2_ANATOMIA},
        {"id": "P2", "nome": "Classificar solicitação de suporte interno", "tecnica": "zero_shot", "versao": "v1", "papel": "controle",
         "descricao_tecnica": "Zero-shot (controle do Experimento 3)", "system": "", "user_template": P2_ZERO_USER, "anatomia": []},
        {"id": "P3", "nome": "E-mail pedindo só os campos que faltaram", "tecnica": "encadeado", "versao": "v1", "papel": "biblioteca",
         "descricao_tecnica": "Prompt encadeado e controle de tom", "system": P3_SYSTEM, "user_template": P3_USER, "anatomia": P3_ANATOMIA},
        {"id": "P3", "nome": "E-mail pedindo só os campos que faltaram", "tecnica": "unico", "versao": "v1", "papel": "controle",
         "descricao_tecnica": "Prompt único que extrai e escreve (controle do Experimento 4)", "system": P3U_SYSTEM, "user_template": P3U_USER, "anatomia": []},
        {"id": "P4", "nome": "Resumir reclamação de cliente em JSON", "tecnica": "saida_estruturada", "versao": "v1", "papel": "biblioteca",
         "descricao_tecnica": "Saída estruturada com regras de não inventar", "system": P4_SYSTEM, "user_template": P4_USER, "anatomia": P4_ANATOMIA},
        {"id": "P5", "nome": "Decidir a próxima etapa da solicitação", "tecnica": "chain_of_thought", "versao": "v1", "papel": "biblioteca",
         "descricao_tecnica": "Chain-of-thought com raciocínio separado da saída", "system": P5_COT_SYSTEM, "user_template": P5_USER, "anatomia": P5_ANATOMIA},
        {"id": "P5", "nome": "Decidir a próxima etapa da solicitação", "tecnica": "direto", "versao": "v1", "papel": "controle",
         "descricao_tecnica": "Sem raciocínio (controle do Experimento 5)", "system": P5_DIRETO_SYSTEM, "user_template": P5_USER, "anatomia": []},
    ]
    return d


def nome_arquivo(d):
    return f"{d['id']}_{d['tecnica']}_{d['versao']}.json"


def hash_de(d):
    return pl.hash_prompt(d["system"], d["user_template"])


def anatomia_resolvida(d):
    """Lista de {parte, rotulo, trecho, funcao}; falha se um trecho não existir literalmente no prompt."""
    texto = d["system"] + "\n---\n" + d["user_template"]
    saida = []
    for parte, trecho, funcao in d["anatomia"]:
        assert parte in PARTES, f"parte desconhecida: {parte}"
        assert trecho in texto, f"{d['id']} {d['tecnica']}: trecho da anatomia não está no prompt: {trecho[:60]!r}"
        saida.append({"parte": parte, "rotulo": PARTES[parte], "trecho": trecho, "funcao": funcao})
    return saida


def conteudo_arquivo(d):
    out = {k: d[k] for k in ["id", "nome", "tecnica", "versao", "papel", "descricao_tecnica"]}
    if "origem" in d:
        out["origem"] = d["origem"]
    out.update({"system": d["system"], "user_template": d["user_template"], "hash12": hash_de(d), "anatomia": anatomia_resolvida(d)})
    return out


def gerar():
    PASTA.mkdir(exist_ok=True)
    for d in definicoes():
        c = conteudo_arquivo(d)
        (PASTA / nome_arquivo(d)).write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(nome_arquivo(d), c["hash12"])


def segmentar(texto, anatomia):
    """Divide `texto` em segmentos [{texto, parte, funcao}] marcando os trechos da anatomia (parte None = sem marca).

    Cada trecho é procurado a partir do início; trecho que se sobrepõe a um anterior é descartado. A soma dos
    segmentos é sempre igual ao texto original (testado)."""
    marcas = []
    for a in anatomia:
        i = texto.find(a["trecho"])
        if i >= 0:
            marcas.append((i, i + len(a["trecho"]), a["parte"], a["funcao"]))
    marcas.sort()
    limpas, fim = [], 0
    for ini, f, parte, funcao in marcas:
        if ini >= fim:
            limpas.append((ini, f, parte, funcao))
            fim = f
    segs, pos = [], 0
    for ini, f, parte, funcao in limpas:
        if ini > pos:
            segs.append({"texto": texto[pos:ini], "parte": None, "funcao": None})
        segs.append({"texto": texto[ini:f], "parte": parte, "funcao": funcao})
        pos = f
    if pos < len(texto):
        segs.append({"texto": texto[pos:], "parte": None, "funcao": None})
    return segs


def carregar(id_, tecnica, versao="v1"):
    return json.loads((PASTA / f"{id_}_{tecnica}_{versao}.json").read_text(encoding="utf-8"))


def montar(prompt, texto):
    return pl.montar(prompt, texto)


if __name__ == "__main__":
    gerar()
