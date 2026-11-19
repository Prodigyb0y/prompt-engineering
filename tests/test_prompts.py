import json

import prompts_lib as p


def test_arquivos_batem_com_o_gerador_e_hash():
    for d in p.definicoes():
        arq = p.PASTA / p.nome_arquivo(d)
        salvo = json.loads(arq.read_text(encoding="utf-8"))
        assert salvo["system"] == d["system"] and salvo["user_template"] == d["user_template"], f"{arq.name} diverge do gerador (crie v2, não edite a v1)"
        assert salvo["hash12"] == p.hash_prompt(salvo["system"], salvo["user_template"])
        assert len(salvo["hash12"]) == 12


def test_t4_usa_system_e_os_outros_nao():
    d = {x["id"]: x for x in p.definicoes()}
    assert d["T4"]["system"] and not d["T1"]["system"] and not d["T2"]["system"] and not d["T3"]["system"]


def test_t2_tem_os_3_exemplos_e_t1_nenhum():
    d = {x["id"]: x for x in p.definicoes()}
    assert d["T2"]["user_template"].count("Exemplo ") == 3
    assert "Exemplo " not in d["T1"]["user_template"] and "Exemplo " not in d["T4"]["user_template"]


def test_t3_pede_os_dois_blocos():
    t = p.carregar("T3")["user_template"]
    assert "<raciocinio>" in t and "<json>" in t


def test_montar_troca_so_o_marcador():
    _, u = p.montar(p.carregar("T1"), "pedido X {texto}")
    assert "pedido X {texto}" in u and u.count("pedido X") == 1


def test_prompts_nao_contem_casos_de_teste():
    casos = json.loads((p.RAIZ / "dados" / "casos_teste.json").read_text(encoding="utf-8"))
    tudo = " ".join(d["system"] + d["user_template"] for d in p.definicoes())
    assert not any(c["texto"] in tudo for c in casos)
