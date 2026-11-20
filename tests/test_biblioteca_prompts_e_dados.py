import json
import re
import shutil

import pytest

import gerar_dados_biblioteca as gd
import prompts_biblioteca as pb
import prompts_lib as pl
import validar_dados_biblioteca as vd


def test_arquivos_batem_com_o_gerador_e_com_o_hash():
    for d in pb.definicoes():
        salvo = json.loads((pb.PASTA / pb.nome_arquivo(d)).read_text(encoding="utf-8"))
        assert salvo == pb.conteudo_arquivo(d), f"{pb.nome_arquivo(d)} diverge do gerador (crie nova versão, não edite uma medida)"
        assert len(salvo["hash12"]) == 12 and salvo["hash12"] == pl.hash_prompt(salvo["system"], salvo["user_template"])


def test_p1_e_o_t4_v2_ja_medido_com_o_mesmo_hash():
    p1 = pb.carregar("P1", "system_prompt", "v2")
    t4 = pl.carregar("T4", "v2")
    assert p1["hash12"] == t4["hash12"] == "2c3ccc1873da"
    assert p1["system"] == t4["system"] and p1["user_template"] == t4["user_template"]


def test_prompts_antigos_mantem_os_hashes_da_rodada_original():
    esperado = {("T1", "v1"): "1ef67d6a52fc", ("T2", "v1"): "be0e8998a563", ("T3", "v1"): "b3a7a7a94ceb",
                ("T4", "v1"): "bb14abcde430", ("T4", "v2"): "2c3ccc1873da"}
    for (t, v), h in esperado.items():
        assert pl.carregar(t, v)["hash12"] == h


def test_anatomia_so_tem_trechos_literais_do_prompt_e_cada_prompt_da_biblioteca_tem_papel_e_tarefa():
    for d in pb.definicoes():
        res = pb.anatomia_resolvida(d)          # falha se o trecho não existir no prompt
        if d["papel"] == "biblioteca":
            partes = {a["parte"] for a in res}
            assert "regras" in partes and ("formato_saida" in partes), d["id"]
            assert "papel" in partes or d["id"] == "P2"
        else:
            assert d["anatomia"] == []


def test_cada_prompt_tem_um_unico_marcador_de_entrada():
    for d in pb.definicoes():
        assert (d["system"] + d["user_template"]).count("{texto}") == 1, d["id"]


def test_prompts_nao_contem_casos_de_teste():
    tudo = " ".join(d["system"] + d["user_template"] for d in pb.definicoes())
    for nome in ("p2", "p3", "p4", "p5"):
        for c in json.loads((gd.DADOS / nome / "casos_teste.json").read_text(encoding="utf-8")):
            assert c["texto"] not in tudo, f"{nome} {c['id']} aparece dentro de um prompt"


def test_politica_do_p5_usa_as_mesmas_constantes_do_gabarito():
    pol = pb.P5_POLITICA
    assert "R$ 5.000,00" in pol and all(f in pol for f in pb.HOMOLOGADOS) and all(i in pol for i in pb.CONTROLADOS)


def test_controles_diferem_so_no_que_o_experimento_testa():
    cot, direto = pb.carregar("P5", "chain_of_thought"), pb.carregar("P5", "direto")
    assert cot["system"].startswith(pb.P5_POLITICA) and direto["system"].startswith(pb.P5_POLITICA)
    assert "<raciocinio>" in cot["system"] and "<raciocinio>" not in direto["system"]
    zero, few = pb.carregar("P2", "zero_shot"), pb.carregar("P2", "few_shot")
    assert "Exemplo " not in zero["user_template"] and few["user_template"].count("Exemplo ") == len(pb.EXEMPLOS_P2) == 6
    assert pb.P2_DEFINICOES in zero["user_template"] and pb.P2_DEFINICOES in few["user_template"]


# ------------------------------------------------------------------ dados
def test_dados_congelados_batem_com_os_hashes():
    assert vd.conferir_congelamento() == []


def test_validacao_independente_passa_nos_dados_atuais():
    assert vd.validar() == []


def test_geracao_e_deterministica_e_igual_ao_congelado(tmp_path):
    gd.gerar_tudo(tmp_path)
    for nome in ("p2", "p3", "p4", "p5"):
        for arq in ("casos_teste.json", "gabarito.json", "registros_fonte.json"):
            assert (tmp_path / nome / arq).read_bytes() == (gd.DADOS / nome / arq).read_bytes(), f"{nome}/{arq}"


def test_vinte_casos_por_prompt_com_bordas():
    for nome in ("p2", "p3", "p4", "p5"):
        casos = json.loads((gd.DADOS / nome / "casos_teste.json").read_text(encoding="utf-8"))
        assert len(casos) == 20 and len({c["id"] for c in casos}) == 20
    p2 = json.loads((gd.DADOS / "p2" / "casos_teste.json").read_text(encoding="utf-8"))
    assert sum(c["tipo"] == "borda" for c in p2) == 8


def _copia(tmp_path):
    destino = tmp_path / "b"
    shutil.copytree(gd.DADOS, destino)
    return destino


def _mutar(destino, nome, mutacao):
    g = json.loads((destino / nome / "gabarito.json").read_text(encoding="utf-8"))
    mutacao(g)
    (destino / nome / "gabarito.json").write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")


@pytest.mark.parametrize("nome,mutacao", [
    ("p3", lambda g: g["E02"].update(faltantes=[])),
    ("p4", lambda g: g["R12"].update(sentimento="insatisfeito")),
    ("p4", lambda g: g["R19"].update(numero_pedido="PED-04821")),
    ("p5", lambda g: g["A09"].update(decisao="escalar")),
    ("p2", lambda g: g["S16"].update(urgencia="baixa")),
])
def test_validador_detecta_gabarito_adulterado(tmp_path, nome, mutacao):
    d = _copia(tmp_path)
    _mutar(d, nome, mutacao)
    assert vd.validar(d), "o validador deveria acusar o gabarito adulterado"


def test_congelamento_acusa_arquivo_alterado(tmp_path):
    d = _copia(tmp_path)
    _mutar(d, "p5", lambda g: g["A01"].update(decisao="aprovar"))
    assert vd.conferir_congelamento(d) == ["p5/gabarito.json"]


def test_dados_sem_nomes_reais_e_so_fornecedores_ficticios():
    import gerar_dados as g1
    for c in json.loads((gd.DADOS / "p3" / "casos_teste.json").read_text(encoding="utf-8")):
        achados = re.findall(r"(?:com a |Fornecedor: |cotação feita com )([^.]+)", c["texto"])
        assert all(a.strip() in g1.FORNECEDORES for a in achados)
