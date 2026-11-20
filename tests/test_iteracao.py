import comparar_iteracao as ci
import prompts_lib as p

CASOS = [{"id": "D01", "tipo": "completa"}, {"id": "D02", "tipo": "valor_total"}, {"id": "D03", "tipo": "valor_total"}]


def reg(caso, rep, ok, custo=0.0001):
    return {"caso": caso, "repeticao": rep, "custo_usd": custo, "tokens_saida": 100, "avaliacao": {"caso_correto": ok}}


def test_t4_v2_so_acrescenta_a_regra_do_valor_total_e_ajusta_a_regra_de_moeda():
    v1, v2 = p.T4_SYSTEM, p.T4_SYSTEM_V2
    assert v1 != v2
    assert "divida o total pela quantidade" in v2 and "divida o total pela quantidade" not in v1
    assert "(nem unitário, nem total)" in v2
    # o resto do prompt permanece igual: removendo as linhas alteradas, as demais são idênticas
    l1, l2 = set(v1.splitlines()), set(v2.splitlines())
    assert len(l1 - l2) == 1 and len(l2 - l1) == 2


def test_prompts_v1_continuam_com_os_hashes_originais():
    assert p.carregar("T4", "v1")["hash12"] == "bb14abcde430"
    assert p.carregar("T4", "v2")["hash12"] == p.hash_prompt(p.T4_SYSTEM_V2, p.T4_USER)


def test_comparar_conta_por_tipo_e_acha_regressao():
    base = [reg("D01", r, True) for r in (1, 2, 3)] + [reg("D02", r, False) for r in (1, 2, 3)] + [reg("D03", r, False) for r in (1, 2, 3)]
    nova = [reg("D01", 1, True), reg("D01", 2, False), reg("D01", 3, True)] + [reg("D02", r, True) for r in (1, 2, 3)] + [reg("D03", r, False) for r in (1, 2, 3)]
    c = ci.comparar(base, nova, CASOS)
    assert c["por_tipo"]["valor_total"]["certas_v1"] == 0 and c["por_tipo"]["valor_total"]["certas_v2"] == 3
    assert c["por_tipo"]["completa"]["certas_v1"] == 3 and c["por_tipo"]["completa"]["certas_v2"] == 2
    assert c["melhorou"] == ["D02"] and c["piorou"] == ["D01"]
    txt = ci.relatorio(c, ["-a", "+b"])
    assert "Casos em que o v2 acertou menos que o v1: D01." in txt and "desenvolvimento" in txt
    assert c["p_sinal"] == 1.0 and "1 casos melhoraram, 1 pioraram" in txt
