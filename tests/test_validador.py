import json

import validador as v

G = {"solicitante_area": "Compras", "item": "papel A4", "quantidade": 10, "unidade": "cx",
     "prazo_entrega": "2026-12-15", "valor_unitario": 1200.0, "moeda": "BRL", "fornecedor": "Papelaria Aurora Ltda"}


def r(**mudancas):
    return json.dumps({**G, **mudancas})


def test_resposta_perfeita():
    a = v.avaliar(r(), G, "T1")
    assert a["caso_correto"] and a["json_valido"] and a["schema_valido"] and all(a["campos"].values())


def test_normalizacao_acento_caixa_espaco():
    assert v.campo_igual("  PAPELARIA  aurora LTDA ", "Papelaria Aurora Ltda")
    assert v.campo_igual("Manutenção", "manutencao")


def test_numeros_exatos():
    assert v.campo_igual(5, 5.0) and v.campo_igual(12.5, 12.5)
    assert not v.campo_igual("5", 5)          # string não vale
    assert not v.campo_igual(True, 1)         # bool não vale
    assert not v.campo_igual(12.51, 12.5)


def test_null_so_igual_a_null():
    assert v.campo_igual(None, None)
    assert not v.campo_igual("", None) and not v.campo_igual(None, "x") and not v.campo_igual(0, None)


def test_data_errada_erra_so_o_campo():
    a = v.avaliar(r(prazo_entrega="2026-12-16"), G, "T1")
    assert not a["caso_correto"] and a["campos"]["prazo_entrega"] is False
    assert sum(a["campos"].values()) == 7


def test_data_fora_do_iso_invalida_schema():
    a = v.avaliar(r(prazo_entrega="15/12/2026"), G, "T1")
    assert not a["schema_valido"] and not a["caso_correto"]


def test_campo_extra_reprova_schema():
    a = v.avaliar(json.dumps({**G, "extra": 1}), G, "T1")
    assert a["json_valido"] and not a["schema_valido"] and not a["caso_correto"]


def test_unidade_fora_do_enum():
    a = v.avaliar(r(unidade="caixas"), G, "T1")
    assert not a["schema_valido"] and not a["caso_correto"]


def test_texto_fora_do_json_invalida():
    assert not v.avaliar("Claro! " + r(), G, "T1")["json_valido"]
    assert not v.avaliar("não é json", G, "T4")["json_valido"]


def test_cerca_markdown_tolerada():
    assert v.avaliar("```json\n" + r() + "\n```", G, "T4")["caso_correto"]


def test_t3_le_so_o_bloco_json():
    ok = "<raciocinio>{\"a\": 1} pensando</raciocinio>\n<json>" + r() + "</json>"
    assert v.avaliar(ok, G, "T3")["caso_correto"]
    assert not v.avaliar("<raciocinio>x</raciocinio> " + r(), G, "T3")["json_valido"]  # sem <json>


def test_json_que_nao_e_objeto():
    assert not v.avaliar("[1, 2]", G, "T1")["json_valido"]


def test_campo_ausente_conta_como_erro():
    d = {k: x for k, x in G.items() if k != "fornecedor"}
    a = v.avaliar(json.dumps(d), G, "T1")
    assert a["campos"]["fornecedor"] is False and not a["caso_correto"]
