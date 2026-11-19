"""Prompts versionados. Fonte única: este módulo gera os arquivos em prompts/.

Cada prompt tem versão e hash SHA-256 (12 caracteres) calculado sobre
system + user_template. Mudou o texto -> o hash muda -> crie v2 (não edite a v1
depois de ver resultado).
"""
import hashlib
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "prompts"
FEWSHOT = RAIZ / "dados" / "exemplos_fewshot.json"

SCHEMA = """Campos do JSON (use exatamente estes nomes, sem campos extras):
- solicitante_area: string ou null
- item: string
- quantidade: número
- unidade: um de "un", "kg", "m", "l", "cx"
- prazo_entrega: data no formato AAAA-MM-DD ou null
- valor_unitario: número ou null
- moeda: "BRL", "USD", "EUR" ou null
- fornecedor: string ou null"""

INSTRUCAO = ("Extraia os dados da solicitação de compra abaixo e responda com um único objeto JSON, "
             "sem texto antes ou depois.")

T1_USER = f"{INSTRUCAO}\n\n{SCHEMA}\n\nSolicitação:\n{{texto}}"

T3_USER = (f"Extraia os dados da solicitação de compra abaixo.\n\n{SCHEMA}\n\n"
           "Primeiro raciocine passo a passo dentro de <raciocinio></raciocinio>. "
           "Depois escreva o objeto JSON final dentro de <json></json>, sem mais nada dentro dessa tag.\n\n"
           "Solicitação:\n{texto}")

T4_SYSTEM = f"""Você é um assistente de extração de dados do setor de compras da Gutenberg Systems, empresa fictícia.
Sua única tarefa é ler uma solicitação de compra em texto livre e devolver um objeto JSON.

{SCHEMA}

Regras:
- Responda somente com o objeto JSON, sem explicações e sem formatação extra.
- Se uma informação não estiver no texto, use null. Não invente valores.
- quantidade é a quantidade do item pedido; ignore outras quantidades citadas no texto (estoque, pedidos anteriores).
- valor_unitario é um número puro, sem símbolo. Entenda separadores brasileiros: "R$ 1.200,00" é 1200 e "R$ 12,50" é 12.5.
- moeda vem do símbolo: R$ = "BRL", US$ = "USD", € = "EUR". Sem valor no texto, valor_unitario e moeda são null.
- prazo_entrega só recebe data quando o texto traz uma data completa com dia, mês e ano. Converta para AAAA-MM-DD. Prazos relativos ("daqui 15 dias", "semana que vem") viram null.
- fornecedor: copie o nome como aparece no texto, mesmo que seja um apelido.
- Ignore ruído, saudações, assinaturas e erros de digitação."""

T4_USER = "Solicitação:\n{texto}"


def _fewshot_bloco():
    ex = json.loads(FEWSHOT.read_text(encoding="utf-8"))
    partes = []
    for i, e in enumerate(ex, 1):
        saida = json.dumps(e["saida"], ensure_ascii=False)
        partes.append(f"Exemplo {i}\nSolicitação:\n{e['entrada']}\nJSON:\n{saida}")
    return "\n\n".join(partes)


def definicoes():
    t2_user = f"{INSTRUCAO}\n\n{SCHEMA}\n\n{_fewshot_bloco()}\n\nAgora a solicitação real\nSolicitação:\n{{texto}}\nJSON:"
    return [
        {"id": "T1", "tecnica": "zero_shot", "versao": "v1", "system": "", "user_template": T1_USER},
        {"id": "T2", "tecnica": "few_shot", "versao": "v1", "system": "", "user_template": t2_user},
        {"id": "T3", "tecnica": "chain_of_thought", "versao": "v1", "system": "", "user_template": T3_USER},
        {"id": "T4", "tecnica": "system_prompt", "versao": "v1", "system": T4_SYSTEM, "user_template": T4_USER},
    ]


def hash_prompt(system: str, user_template: str) -> str:
    return hashlib.sha256((system + "\n---\n" + user_template).encode("utf-8")).hexdigest()[:12]


def nome_arquivo(d):
    return f"{d['id']}_{d['tecnica']}_{d['versao']}.json"


def gerar():
    PASTA.mkdir(exist_ok=True)
    for d in definicoes():
        d = {**d, "hash12": hash_prompt(d["system"], d["user_template"])}
        (PASTA / nome_arquivo(d)).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(nome_arquivo(d), d["hash12"])


def carregar(id_tecnica: str, versao: str = "v1"):
    for arq in sorted(PASTA.glob(f"{id_tecnica}_*_{versao}.json")):
        return json.loads(arq.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"prompt {id_tecnica} {versao} não encontrado")


def montar(prompt: dict, texto: str):
    """Devolve (system, user) para um caso. Troca só o marcador {texto}."""
    return prompt["system"], prompt["user_template"].replace("{texto}", texto)


if __name__ == "__main__":
    gerar()
