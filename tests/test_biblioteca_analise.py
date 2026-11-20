import json

import pytest

import analisar_biblioteca as ab
import experimentos as ex
from test_biblioteca_avaliacao_e_execucao import Falso, cliente_falso


def _rodar(tmp_path, falso=None, so=None):
    cli, _ = cliente_falso(tmp_path, falso)
    for exp, var in ex.ORDEM:
        if so and (exp, var) not in so:
            continue
        ex.executar_variante(cli, exp, var, pasta=tmp_path / "brutos")
    return tmp_path / "brutos"


def test_sem_respostas_nada_e_estimado(tmp_path):
    r = ab.resumir_tudo(tmp_path / "vazio", tmp_path / "sem_piloto")
    assert all(v == {"medido": False} for v in r["variantes"].values())
    assert all(c["medido"] is False for c in r["comparacoes"].values())
    assert r["custo_novo_usd"]["total"] == 0 and r["chamadas_novas"] == 0
    assert "não medido" in ab.relatorio(r)


def test_resumo_de_rodada_completa_com_cliente_falso(tmp_path):
    brutos = _rodar(tmp_path)
    r = ab.resumir_tudo(brutos, tmp_path / "sem_piloto")
    v = r["variantes"]["E5/cot"]
    assert v["medido"] and v["completo"] and v["respostas"] == 60 and v["casos"] == 20 and v["repeticoes"] == 3
    assert v["acerto_caso_media"] == 1.0 and v["acerto_caso_rep_min"] == v["acerto_caso_rep_max"] == 1.0
    # custo: 1000 tokens de entrada e 100 de saída por chamada
    por_chamada = 1000 * 0.10e-6 + 100 * 0.50e-6
    assert v["custo_por_resposta_usd"] == pytest.approx(por_chamada)
    assert r["variantes"]["E4/encadeado"]["custo_por_resposta_usd"] == pytest.approx(2 * por_chamada)
    assert r["variantes"]["E4/encadeado"]["chamadas_por_resposta"] == 2
    assert r["custo_novo_usd"]["rodadas"] == pytest.approx(sum(x["custo_total_usd"] for x in r["variantes"].values()))
    assert r["chamadas_novas"] == 120 + 180 + 60 + 120 - 0 and r["variantes"]["E3/few_shot"]["truncadas"] == 0
    c = r["comparacoes"]["E4"]
    assert c["razao_custo"] == pytest.approx(2.0) and c["p_sinal"] == 1.0 and c["a_favor_base"] == c["a_favor_alternativa"] == 0


class Errado(Falso):
    """Erra o P2 em 2 casos de borda na variante few-shot (para testar a comparação)."""

    def __call__(self, system, user, max_tokens):
        r = super().__call__(system, user, max_tokens)
        if "Categorias (escolha uma)" in user and "Exemplo 1" not in user:      # zero-shot
            cid = self._achar("p2", user)
            if cid in ("S13", "S14"):
                r["texto"] = json.dumps({"categoria": "acesso", "urgencia": "baixa"})
        return r


def test_comparacao_pareada_conta_casos_a_favor(tmp_path):
    brutos = _rodar(tmp_path, Errado(), so=[("E3", "zero_shot"), ("E3", "few_shot")])
    r = ab.resumir_tudo(brutos, tmp_path / "sem_piloto")
    c = r["comparacoes"]["E3"]
    assert c["a_favor_alternativa"] == 2 and c["a_favor_base"] == 0 and c["casos_melhores_na_alternativa"] == ["S13", "S14"]
    assert c["p_sinal"] == pytest.approx(0.5)             # 2 casos discordantes, todos na mesma direção: p = 2 * (1/4)
    assert c["diferenca_acerto_pp"] == pytest.approx(10.0)
    assert r["variantes"]["E3/zero_shot"]["acerto_caso_media"] == pytest.approx(0.9)
    assert r["comparacoes"]["E5"]["medido"] is False       # E5 sem respostas


def test_variante_incompleta_e_marcada(tmp_path):
    cli, _ = cliente_falso(tmp_path)
    ex.executar_variante(cli, "P4", "saida_estruturada", pasta=tmp_path / "b", limite_casos=4)
    v = ab.resumir_tudo(tmp_path / "b", tmp_path / "x")["variantes"]["P4/saida_estruturada"]
    assert v["medido"] and v["completo"] is False and v["casos"] == 4
    assert v["extras"]["invencoes_total"] == 0
