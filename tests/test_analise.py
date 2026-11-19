import analisar as a


def reg(t, caso, rep, ok, custo=0.001, lat=1.0, tipo="completa", stop="end_turn", valido=True):
    return {"tecnica": t, "prompt_hash12": "abc123abc123", "prompt_versao": "v1", "caso": caso, "tipo": tipo, "repeticao": rep,
            "tokens_entrada": 100, "tokens_saida": 50, "custo_usd": custo, "latencia_s": lat, "stop_reason": stop,
            "avaliacao": {"json_valido": valido, "schema_valido": valido, "caso_correto": ok, "campos": {c: ok for c in a.CAMPOS}}}


def dados():
    r = []
    for i in range(50):
        for rep in (1, 2, 3):
            r.append(reg("T1", f"C{i:02d}", rep, ok=(i < 25 or rep == 1 and i < 30), custo=0.002, lat=float(rep)))
            r.append(reg("T4", f"C{i:02d}", rep, ok=True, custo=0.001))
    return r


def test_acerto_custo_e_latencia_batem_com_conta_manual():
    s = a.resumir(dados())
    # T1: 25 casos sempre certos + 5 casos certos só na repetição 1 (1/3 cada)
    assert s["T1"]["acerto_caso_media"] == (25 + 5 / 3) / 50
    assert s["T1"]["acerto_caso_rep_max"] == 30 / 50 and s["T1"]["acerto_caso_rep_min"] == 25 / 50
    assert s["T1"]["custo_total_usd"] == 150 * 0.002
    assert s["T1"]["custo_por_acerto_usd"] == (150 * 0.002) / (25 * 3 + 5)
    assert s["T1"]["latencia_media_s"] == 2.0 and s["T1"]["latencia_mediana_s"] == 2.0
    assert s["T4"]["acerto_caso_media"] == 1.0 and s["T4"]["custo_por_caso_usd"] == 0.001


def test_bootstrap_e_deterministico_e_contem_a_media():
    v = [1.0] * 30 + [0.0] * 20
    lo, hi = a.bootstrap_ic(v)
    assert (lo, hi) == a.bootstrap_ic(v) and lo < 0.6 < hi


def test_ic_sobreposto_nao_declara_vencedor():
    r = []
    for i in range(50):
        r.append(reg("T1", f"C{i:02d}", 1, ok=i < 48))
        r.append(reg("T4", f"C{i:02d}", 1, ok=True))
    s = a.resumir(r)
    assert s["T4"]["acerto_caso_media"] > s["T1"]["acerto_caso_media"]
    assert a.separaveis(s) == []                       # 96% vs 100%: intervalos se sobrepõem
    assert "Nenhuma técnica pode ser declarada melhor" in a.relatorio(s, None)


def test_diferenca_grande_e_declarada():
    r = []
    for i in range(50):
        r.append(reg("T1", f"C{i:02d}", 1, ok=i < 10))
        r.append(reg("T4", f"C{i:02d}", 1, ok=True))
    assert a.separaveis(a.resumir(r)) == [("T4", "T1")]


def test_truncadas_json_invalido_e_sem_acerto():
    r = [reg("T3", f"C{i:02d}", 1, ok=False, valido=False, stop="max_tokens") for i in range(50)]
    s = a.resumir(r)["T3"]
    assert s["truncadas"] == 50 and s["json_valido"] == 0 and s["custo_por_acerto_usd"] is None
    assert "n/a" in a.relatorio(a.resumir(r), 0.5)


def _r(resposta, campos_ok, tec="T1"):
    import validador as v
    g = {"solicitante_area": None, "item": "papel", "quantidade": 1, "unidade": "un", "prazo_entrega": None,
         "valor_unitario": None, "moeda": None, "fornecedor": "Papelaria Aurora Ltda"}
    return g, {"tecnica": tec, "resposta": resposta, "avaliacao": v.avaliar(resposta, g, tec)}


def test_classifica_ponto_final_do_fornecedor():
    import json
    import classificar_erros as ce
    g, r = _r(json.dumps({"solicitante_area": None, "item": "papel", "quantidade": 1, "unidade": "un", "prazo_entrega": None,
                          "valor_unitario": None, "moeda": None, "fornecedor": "Papelaria Aurora Ltda."}), None)
    assert ce.classificar(r, g) == ("fornecedor_ponto_final", True)
    assert r["avaliacao"]["caso_correto"] is False        # o resultado oficial NÃO muda


def test_outras_classes():
    import json
    import classificar_erros as ce
    base = {"solicitante_area": None, "item": "papel", "quantidade": 1, "unidade": "un", "prazo_entrega": None,
            "valor_unitario": None, "moeda": None, "fornecedor": "Papelaria Aurora Ltda"}
    g, r = _r(json.dumps({**base, "fornecedor": "Outra Empresa"}), None)
    assert ce.classificar(r, g) == ("campo_diferente", False)
    g, r = _r(json.dumps({**base, "item": "caneta", "fornecedor": "Papelaria Aurora Ltda."}), None)
    assert ce.classificar(r, g) == ("campo_diferente", False)       # ponto final + outro erro: não perdoa
    g, r = _r("não é json", None)
    assert ce.classificar(r, g) == ("json_invalido", False)
    g, r = _r(json.dumps({**base, "unidade": "caixas"}), None)
    assert ce.classificar(r, g) == ("schema_invalido", False)
    g, r = _r(json.dumps(base), None)
    assert ce.classificar(r, g) == ("correto", True)
