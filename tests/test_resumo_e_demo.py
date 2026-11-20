import json
import re

import pytest

import analisar_biblioteca as ab
import consolidar as co
import conteudo_biblioteca as cb
import experimentos as ex
import gerar_demo as gdm
import prompts_biblioteca as pb
from test_biblioteca_analise import Errado, _rodar

RAIZ = co.RAIZ


def _resumo():
    return json.loads(co.SAIDA.read_text(encoding="utf-8"))


def test_resumo_no_disco_esta_em_dia_com_as_fontes():
    assert co.construir() == _resumo(), "resultados/resumo.json está desatualizado: rode python src/consolidar.py"


def test_e1_usa_os_numeros_originais_da_rodada_v2_sem_reescrever():
    r = _resumo()
    e1 = next(e for e in r["experimentos"] if e["id"] == "E1")
    orig = json.loads((co.EXT_V2 / "resumo.json").read_text(encoding="utf-8"))
    for t in ("T1", "T2", "T3", "T4"):
        assert e1["tecnicas"][t]["acerto"] == orig[t]["acerto_caso_media"]
        assert e1["tecnicas"][t]["custo_resposta_usd"] == orig[t]["custo_por_caso_usd"]
    assert (e1["casos_sem_diferenca"], e1["casos_total"], e1["casos_valor_total"]) == (46, 50, 4)
    assert [e1["tecnicas"][t]["certas_valor_total"] for t in ("T1", "T2", "T3", "T4")] == [10, 1, 12, 0]
    assert "46 de 50" in e1["resultado"]


def test_e2_usa_os_numeros_originais_da_iteracao():
    e2 = next(e for e in _resumo()["experimentos"] if e["id"] == "E2")
    it = json.loads((co.EXT_V2 / "iteracao.json").read_text(encoding="utf-8"))
    assert e2["placar"] == {"antes": 0, "depois": 12, "de": 12, "tipo": "valor total"} and e2["p_sinal"] == it["p_sinal"] == 0.125
    assert e2["hash_v1"] == "bb14abcde430" and e2["hash_v2"] == "2c3ccc1873da" and e2["sem_regressao"] is True
    add = [l["texto"] for l in e2["diff"] if l["tipo"] == "add"]
    dele = [l["texto"] for l in e2["diff"] if l["tipo"] == "del"]
    assert len(add) == 2 and len(dele) == 1                   # "duas linhas" acrescentadas (uma delas substitui a regra de moeda)
    assert any("só o valor total" in x for x in add)


def test_respostas_gravadas_preservadas_recalculam_o_acerto_oficial():
    rg = json.loads((co.EXT_V2 / "respostas_gravadas.json").read_text(encoding="utf-8"))
    orig = json.loads((co.EXT_V2 / "resumo.json").read_text(encoding="utf-8"))
    for t in ("T1", "T2", "T3", "T4"):
        oks = [s["correto"] for c in rg["casos"] for s in c["saidas"][t]]
        assert len(oks) == 150 and sum(oks) / 150 == pytest.approx(orig[t]["acerto_caso_media"])


def test_o_que_nao_foi_medido_nao_tem_numero():
    r = _resumo()
    for e in r["experimentos"]:
        if e["status"] == "nao_medido":
            assert e["resultado"] is None and e["numero"] is None and e["grupos"] == [] and e["quando_usar"] is None and e["comando"].startswith("python src/rodar_biblioteca.py")
    for p in r["prompts"]:
        if not p["medido"]:
            assert p["acerto"] is None and p["custo_chamada_usd"] is None and "não medidos" in p["pendencia"]
    assert [g["medido"] for g in r["playground"] if g["id"] != "E1"] == [False] * 4


def test_custo_soma_o_livro_caixa_e_respeita_o_teto():
    c = _resumo()["custo"]
    assert c["anterior_usd"] == pytest.approx(0.248969) and c["total_usd"] <= c["teto_total_usd"] == 1.0
    assert c["sobra_usd"] == pytest.approx(1.0 - c["total_usd"]) and c["teto_rodadas_novas_usd"] == 0.6


def test_textos_de_conteudo_nao_carregam_resultado_medido():
    # frases de aprendizado do projeto: nenhum percentual nem custo em dólar digitado à mão
    for pid, info in cb.PROMPTS.items():
        for campo in ("problema", "quem_usa", "tecnica_porque", "aprendi_projeto"):
            assert not re.search(r"\d+[,.]\d+\s*%|US\$ ?0[,.]\d", info.get(campo, "")), (pid, campo)
    assert "9 dos meus 20 textos" in cb.PROMPTS["P4"]["aprendi_projeto"]
    assert "Achei 9 textos" in (RAIZ / "dados" / "biblioteca" / "REVISAO_E_LIMITACOES.md").read_text(encoding="utf-8")
    assert "R$ 5.000,00" in cb.PROMPTS["P5"]["aprendi_projeto"] and pb.LIMITE_TXT in pb.P5_POLITICA


# ------------------------------------------------------------------ frases geradas a partir de números
def _v(acerto, custo, **k):
    return {"acerto_caso_media": acerto, "custo_por_resposta_usd": custo, **k}


def _comp(dif, fa, fb, p, razao=2.0, n=20):
    return {"casos_comparados": n, "diferenca_acerto_pp": dif, "a_favor_base": fa, "a_favor_alternativa": fb, "p_sinal": p, "razao_custo": razao,
            "base": "zero_shot", "alternativa": "few_shot"}


def test_interpretacao_empate_ganho_e_perda():
    base, alt = _v(0.9, 0.0001), _v(0.9, 0.0002)
    r, q = co.interpretar("E3", _comp(0.0, 0, 0, 1.0), base, alt)
    assert "Sem diferença" in r and "90,0%" in r and "zero-shot custa menos" in q
    r, q = co.interpretar("E3", _comp(10.0, 0, 2, 0.5), _v(0.8, 0.0001), _v(0.9, 0.0002))
    assert "10,0 pontos a mais" in r and "indício, não uma prova" in r and "p = 0,500" in r and "2,0 vezes" in r
    r, q = co.interpretar("E5", _comp(-5.0, 3, 0, 0.25), _v(0.95, 0.0001), _v(0.9, 0.0005, ), )
    assert "pontos a menos" in r and "piorou" in q


def test_diferenca_so_passa_no_teste_quando_p_menor_que_0_05():
    r, _ = co.interpretar("E4", _comp(30.0, 0, 8, 0.0078), _v(0.6, 0.0001), _v(0.9, 0.0002))
    assert "passa no teste pareado" in r and "indício" not in r


def test_resumo_de_rodada_fake_completa_gera_frases_e_cartoes(tmp_path):
    brutos = _rodar(tmp_path, Errado(), so=[("E3", "zero_shot"), ("E3", "few_shot"), ("E4", "unico"), ("E4", "encadeado"), ("P4", "saida_estruturada"), ("E5", "direto"), ("E5", "cot")])
    r = co.construir(pasta_brutos=brutos, pasta_piloto=tmp_path / "sem")
    e3 = next(e for e in r["experimentos"] if e["id"] == "E3")
    assert e3["status"] == "medido" and "10,0 pontos a mais" in e3["resultado"] and e3["quando_usar"]
    assert [e["status"] for e in r["experimentos"]] == ["medido"] * 5 and r["pendencias"] == []
    assert all(p["medido"] for p in r["prompts"]) and r["projeto"]["experimentos_medidos"] == 5
    p2 = next(p for p in r["prompts"] if p["id"] == "P2")
    assert p2["exemplo"]["gravada"] and p2["custo_chamada_usd"] > 0
    assert all(g["medido"] and len(g["casos"]) >= 18 for g in r["playground"])
    assert r["custo"]["novo_usd"] == pytest.approx(r["custo"]["novo_rodadas_usd"]) and r["custo"]["total_usd"] == pytest.approx(0.248969 + r["custo"]["novo_usd"])
    assert gdm.dados_da_pagina(r)["playground"][1]["casos"]            # a página embute as respostas gravadas novas
    # a página gerada com tudo medido continua abaixo de 1 MB
    assert gdm.gerar(r, saida=tmp_path / "x" / "index.html") < gdm.LIMITE_BYTES


# ------------------------------------------------------------------ segmentos da anatomia
def test_segmentos_reconstroem_o_prompt_sem_perder_nem_repetir_texto():
    for p in _resumo()["prompts"]:
        assert "".join(s["texto"] for s in p["segmentos"]["system"]) == p["system"]
        assert "".join(s["texto"] for s in p["segmentos"]["user"]) == p["user_template"]
        marcados = [s for loc in p["segmentos"].values() for s in loc if s["parte"]]
        assert marcados and {s["parte"] for s in marcados} == {x["parte"] for x in p["partes"]}


def test_segmentar_descarta_sobreposicao():
    segs = pb.segmentar("abcdefghij", [{"trecho": "cdef", "parte": "papel", "funcao": "a"}, {"trecho": "efgh", "parte": "regras", "funcao": "b"}])
    assert "".join(s["texto"] for s in segs) == "abcdefghij" and [s["parte"] for s in segs] == [None, "papel", None]


# ------------------------------------------------------------------ a página
def test_pagina_em_dia_unica_e_leve():
    html = (RAIZ / "docs" / "index.html").read_bytes()
    assert len(html) < gdm.LIMITE_BYTES
    esperado = _gerar_em_memoria()
    assert html.decode("utf-8") == esperado, "docs/index.html está desatualizado: rode python src/gerar_demo.py"


def _gerar_em_memoria():
    dados = json.dumps(gdm.dados_da_pagina(_resumo()), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\!--")
    return gdm.MODELO.read_text(encoding="utf-8").replace(gdm.MARCADOR, dados)



def test_pagina_sem_dependencia_externa_e_com_a_navegacao_pedida():
    html = (RAIZ / "docs" / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"<script[^>]+src=|<link[^>]+href=|@import|url\(\s*['\"]?https?:|<img[^>]+src=['\"]?https?:|cdn\.", html)
    assert html.count("<script") == 2 and html.count("</script>") == 2
    for rotulo in ("Biblioteca", "Experimentos", "Como medi", "Sobre"):
        assert f">{rotulo}</a>" in html
    assert 'data-theme="dark"' in html and "Copiar prompt" in html and "gravadas" in html and "não chamadas ao vivo" in html
    assert "system-ui" in html and "ui-monospace" in html


def test_json_embutido_valido_e_igual_ao_resumo():
    html = (RAIZ / "docs" / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<script id="dados" type="application/json">(.*?)</script>', html, re.DOTALL)
    d = json.loads(m.group(1).replace("<\\/", "</").replace("<\\!--", "<!--"))
    assert d == gdm.dados_da_pagina(_resumo()) and d["projeto"]["prompts"] == 5 and len(d["experimentos"]) == 5


def test_modelo_da_pagina_nao_tem_numero_de_resultado_digitado():
    modelo = gdm.MODELO.read_text(encoding="utf-8")
    assert not re.search(r"\d+[,.]\d+\s*%|\bUS\$ ?0[,.]\d|\b\d{2,3}\s*%\s*(?:de|para)", modelo)
