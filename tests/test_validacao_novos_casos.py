import hashlib
import json
from pathlib import Path

import pytest

import comparar_validacao as cv
import gerar_dados_v3 as g3
import rodar
import validar_dados_v3 as v3

RAIZ = Path(__file__).resolve().parent.parent
V3 = RAIZ / "dados" / "extracao" / "v3"


def _ler(p):
    return json.loads((V3 / p).read_text(encoding="utf-8"))


def test_v3_passa_na_validacao_independente():
    assert v3.validar() == 0


def test_v3_esta_congelada_e_o_hash_confere():
    esperado = {l.split()[1]: l.split()[0] for l in (V3 / "CONGELADO.sha256").read_text().splitlines()}
    assert set(esperado) == {"casos_teste.json", "gabarito.json"}
    for nome, h in esperado.items():
        assert hashlib.sha256((V3 / nome).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == h, f"{nome} (v3) mudou depois do congelamento"


def test_v3_tem_20_casos_novos_e_muitos_de_valor_total():
    casos = _ler("casos_teste.json")
    assert len(casos) == 20 and all(c["id"].startswith("H") for c in casos)
    assert sum(1 for c in casos if c["tipo"] == "valor_total") == 6
    v1 = {c["texto"] for c in json.loads((RAIZ / "dados/extracao/v1/casos_teste.json").read_text(encoding="utf-8"))}
    v2 = {c["texto"] for c in json.loads((RAIZ / "dados/extracao/v2/casos_teste.json").read_text(encoding="utf-8"))}
    fs = {e["entrada"] for e in json.loads((RAIZ / "dados/extracao/v1/exemplos_fewshot.json").read_text(encoding="utf-8"))}
    textos = {c["texto"] for c in casos}
    assert not (textos & v1) and not (textos & v2) and not (textos & fs)


def test_geracao_v3_e_deterministica():
    a, b = g3.gerar(), g3.gerar()
    assert a == b
    assert a[0] == _ler("casos_teste.json") and a[1] == _ler("gabarito.json")


def test_valor_total_do_gabarito_bate_com_a_conta():
    import re
    casos = {c["id"]: c for c in _ler("casos_teste.json")}
    gab = _ler("gabarito.json")
    for cid, c in casos.items():
        if c["tipo"] != "valor_total":
            continue
        m = re.search(r"valor total (?:R\$|US\$|€)\s*([\d.,]+\d)", c["texto"])
        total = float(m[1].replace(".", "").replace(",", ".")) if "," in m[1] else float(m[1])
        assert round(total / gab[cid]["quantidade"], 2) == gab[cid]["valor_unitario"]


class ClienteFalso:
    """T4 v2 devolve o gabarito; T4 v1 erra o valor unitário nos casos de valor total (só para exercitar o fluxo)."""

    def __init__(self, casos, gab):
        self.casos, self.gab, self.chamadas = casos, gab, 0

        class C:
            gasto = 0.0
        self.controle = C()

    def chamar(self, system, user, max_tokens):
        self.chamadas += 1
        caso = next(c for c in self.casos if c["texto"] in user)
        g = dict(self.gab[caso["id"]])
        if "divida o total pela quantidade" not in system and caso["tipo"] == "valor_total":
            g["valor_unitario"] = g["valor_unitario"] * g["quantidade"]
        return {"texto": json.dumps(g, ensure_ascii=False), "tokens_entrada": 500, "tokens_saida": 80, "custo_usd": 0.0001,
                "latencia_s": 0.5, "tentativas": 1, "stop_reason": "end_turn"}


@pytest.fixture
def rodada(tmp_path):
    casos, gab = _ler("casos_teste.json"), _ler("gabarito.json")
    cli = ClienteFalso(casos, gab)
    feitas, novas = rodar.executar_validacao(cli, casos, gab, pasta=tmp_path)
    return casos, gab, cli, tmp_path, feitas, novas


def test_validacao_faz_120_chamadas_em_duas_pastas_e_e_retomavel(rodada):
    casos, gab, cli, pasta, feitas, novas = rodada
    assert (feitas, novas, cli.chamadas) == (0, 120, 120)
    assert len(list((pasta / "v1").glob("*.json"))) == 60 and len(list((pasta / "v2").glob("*.json"))) == 60
    h1 = {json.loads(a.read_text(encoding="utf-8"))["prompt_hash12"] for a in (pasta / "v1").glob("*.json")}
    h2 = {json.loads(a.read_text(encoding="utf-8"))["prompt_hash12"] for a in (pasta / "v2").glob("*.json")}
    assert len(h1) == len(h2) == 1 and h1 != h2
    feitas2, novas2 = rodar.executar_validacao(cli, casos, gab, pasta=pasta)
    assert (feitas2, novas2, cli.chamadas) == (120, 0, 120)


def test_comparacao_da_validacao_aplica_o_criterio_escrito_antes(rodada):
    from analisar import carregar
    import comparar_iteracao as ci
    casos, gab, _, pasta, *_ = rodada
    c = ci.comparar(carregar(pasta / "v1"), carregar(pasta / "v2"), casos)
    v = cv.veredito(c)
    assert v["valor_total_certas_v1"] == 0 and v["valor_total_certas_v2"] == 18 and v["valor_total_respostas"] == 18
    assert v["generaliza"] and not v["regressao"]
    assert v["resto_certas_v1"] == v["resto_certas_v2"] == v["resto_respostas"] == 42
    assert cv.erros_do_v2(carregar(pasta / "v2"), gab) == []
    erros = cv.erros_do_v2(carregar(pasta / "v1"), gab)
    assert len(erros) == 18 and set(e["campos_errados"][0] for e in erros) == {"valor_unitario"}
    txt = cv.relatorio(c, v, [], ci.diff_prompts(), 0)
    assert "Critério (escrito antes de rodar)" in txt and "a regra generalizou" in txt and "sem regressão" in txt


def test_criterio_nao_generaliza_quando_o_v2_erra_mais_de_uma(rodada):
    c = {"por_tipo": {"valor_total": {"casos": 6, "respostas": 18, "certas_v1": 0, "certas_v2": 16, "respostas_v2": 18},
                      "completa": {"casos": 1, "respostas": 3, "certas_v1": 3, "certas_v2": 2, "respostas_v2": 3}}}
    v = cv.veredito(c)
    assert not v["generaliza"] and v["regressao"]


def test_validacao_so_roda_com_pe_versao_v3():
    with pytest.raises(SystemExit):
        rodar.main_validacao()
