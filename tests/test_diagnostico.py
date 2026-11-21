import json

import pytest

import analisar_biblioteca as ab
import diagnostico as dg
import textos_diagnostico as td

EMAIL_PEDIDO = "Assunto: x\n\nOlá,\n\nPara dar andamento, precisamos de:\n\n- prazo de entrega\n- fornecedor\n\nObrigado."
EMAIL_CONFIRMA = "Assunto: x\n\nRecebemos sua solicitação, com fornecedor Alfa. Precisamos do prazo de entrega.\n\nObrigado."


def test_pedido_e_so_o_que_aparece_em_item_de_lista():
    assert dg.campos_pedidos(EMAIL_PEDIDO) == {"prazo_entrega", "fornecedor"}
    assert dg.campos_pedidos("1. Prazo de entrega\n2) Fornecedor") == {"prazo_entrega", "fornecedor"}
    assert dg.campos_pedidos(EMAIL_CONFIRMA) == set()           # frase corrida = menção, não pedido


def _reg(email, citados, esperados):
    return {"resposta": email, "avaliacao": {"caso_correto": set(citados) == set(esperados), "citados": sorted(citados), "esperados": sorted(esperados)}}


def test_classes_de_erro_do_p3():
    gab = {"faltantes": ["prazo_entrega"]}
    assert dg.classificar_resposta_p3(_reg("Assunto: x\n\n- prazo de entrega", ["prazo_entrega"], ["prazo_entrega"]), gab)["classe"] == "correta"
    c = dg.classificar_resposta_p3(_reg(EMAIL_CONFIRMA, ["fornecedor", "prazo_entrega"], ["prazo_entrega"]), gab)
    assert c["classe"] == "so_confirmou_dado_recebido" and c["correta_por_pedido"] and c["so_mencionou"] == ["fornecedor"]
    c = dg.classificar_resposta_p3(_reg(EMAIL_PEDIDO, ["fornecedor", "prazo_entrega"], ["prazo_entrega"]), gab)
    assert c["classe"] == "pediu_campo_que_ja_tinha" and not c["correta_por_pedido"]
    c = dg.classificar_resposta_p3(_reg("Assunto: x\n\n- fornecedor", ["fornecedor"], ["prazo_entrega"]), gab)
    assert c["classe"] == "esqueceu_campo" or c["faltou"] == ["prazo_entrega"]


@pytest.fixture(scope="module")
def d():
    return dg.construir()


def test_diagnostico_bate_com_o_resumo_oficial(d):
    resumo = ab.resumir_tudo()
    for v in ("encadeado", "unico"):
        x = d["E4"][v]
        assert x["acerto_oficial"] == pytest.approx(resumo["variantes"][f"E4/{v}"]["acerto_caso_media"])
        assert sum(x["classes"].values()) == x["erradas"]
    assert d["E3"]["zero_shot"]["erradas"] == round(60 * (1 - resumo["variantes"]["E3/zero_shot"]["acerto_caso_media"]))
    assert d["E4"]["extracao_p1_certa_em_todas"]["de"] == 60


def test_o_que_o_diagnostico_encontrou(d):
    assert d["E4"]["extracao_p1_certa_em_todas"]["certas"] == 60 and d["E4"]["encadeado"]["extracao_p1_errada_nas_erradas"] == 0
    assert d["E4"]["encadeado"]["classes"].get("esqueceu_campo", 0) == 0 and d["E4"]["unico"]["classes"].get("esqueceu_campo", 0) == 0
    assert set(d["E3"]["zero_shot"]["campo_errado"]) == {"urgencia"}
    assert set(d["P4"]["campo_errado"]) == {"sentimento"} and d["P4"]["invencoes"] == 0
    assert d["E5"]["cot"]["erradas"] == 0 and d["E5"]["direto"]["com_duas_decisoes"] >= 1


def test_textos_trazem_os_numeros_do_diagnostico(d):
    enc = d["E4"]["encadeado"]
    assert str(enc["erradas"]) in td.aprendi_p3(d) and "60 de 60" in td.aprendi_p3(d)
    e4 = " ".join(td.explicacao_e4(d)["paragrafos"])
    assert ab.pct(enc["acerto_pedido"]) in e4 and ab.pct(d["E4"]["unico"]["acerto_pedido"]) in e4 and "não substitui o número oficial" in e4
    assert "urgência" in td.aprendi_p2(d) and "sentimento" in td.aprendi_p4(d) and "duas decisões" in td.aprendi_p5(d)


def test_resumo_usa_os_textos_pos_medicao():
    r = json.loads((dg.RAIZ / "resultados" / "resumo.json").read_text(encoding="utf-8"))
    por_id = {p["id"]: p for p in r["prompts"]}
    for pid in ("P2", "P3", "P4", "P5"):
        assert por_id[pid]["aprendi_preparo"] and por_id[pid]["aprendi"] != por_id[pid]["aprendi_preparo"]
    exps = {e["id"]: e for e in r["experimentos"]}
    for eid in ("E3", "E4", "E5"):
        assert exps[eid]["explicacao"]["paragrafos"]
    assert any(x["titulo"].startswith("Encadear ou não depende") for x in r["conclusao"]["pode"])
