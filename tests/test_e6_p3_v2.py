import json
import sys

import pytest

import analisar_biblioteca as ab
import experimentos as ex
import prompts_biblioteca as pb
import rodar_biblioteca as rb
from test_biblioteca_avaliacao_e_execucao import Falso, cliente_falso


def test_p3_v1_continua_igual_e_o_v2_e_outro_prompt():
    v1, v2 = pb.carregar("P3", "encadeado", "v1"), pb.carregar("P3", "encadeado", "v2")
    assert v1["hash12"] == "333d7e7cff49"
    assert v2["hash12"] != v1["hash12"] and v2["hash12"] == pb.pl.hash_prompt(pb.P3V2_SYSTEM, pb.P3_USER)
    assert v2["papel"] == "iteracao" and v2["versao"] == "v2" and v2["anatomia"]
    # o v2 nasce do diagnóstico: decidir pelo null, listar um por linha e nunca citar campo preenchido
    assert "cujo valor é null" in v2["system"] and 'começando com "- "' in v2["system"]
    assert "nem para confirmar que recebeu" in v2["system"]
    assert "nem para confirmar" not in v1["system"]
    # tom, formato e vocabulário continuam os do v1
    for trecho in ['"área solicitante"', '"prazo de entrega"', '"valor unitário" (peça também a moeda)', '"fornecedor"',
                   "Tom: profissional e cordial", "até 120 palavras", "Equipe de Compras · Gutenberg Systems", pb.P3_SENTINELA]:
        assert trecho in v1["system"] and trecho in v2["system"]


def test_o_p3_v2_nao_vira_cartao_da_biblioteca():
    assert [d["papel"] for d in pb.definicoes() if d["id"] == "P3" and d["versao"] == "v2"] == ["iteracao"]
    assert sum(1 for d in pb.definicoes() if d["papel"] == "biblioteca") == 5


def test_e6_usa_o_mesmo_fluxo_do_e4_trocando_so_o_email(tmp_path):
    assert ex.VARIANTES[("E6", "encadeado_v2")]["passos"] == [("P1", "system_prompt", "v2"), ("P3", "encadeado", "v2")]
    assert ex.VARIANTES[("E4", "encadeado")]["passos"][0] == ex.VARIANTES[("E6", "encadeado_v2")]["passos"][0]
    falso = Falso()
    cli, _ = cliente_falso(tmp_path, falso)
    ex.executar_variante(cli, "E6", "encadeado_v2", pasta=tmp_path / "b", limite_casos=2, reps=1)
    assert falso.n == 4
    reg = json.loads((tmp_path / "b" / "E6_encadeado_v2.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert [(e["prompt"], e["versao"]) for e in reg["etapas"]] == [("P1", "v2"), ("P3", "v2")]
    assert reg["etapas"][1]["hash12"] == pb.carregar("P3", "encadeado", "v2")["hash12"]


def test_piloto_do_p3_v2_faz_5_chamadas_sem_mexer_no_piloto_original(tmp_path):
    (tmp_path / "piloto.json").write_text('{"original": true}', encoding="utf-8")
    falso = Falso()
    cli, _ = cliente_falso(tmp_path, falso)
    r = ex.executar_piloto_p3v2(cli, pasta=tmp_path)
    assert falso.n == 5 and r["chamadas"] == 5 and r["acertos"] == 5 and r["erro"] is None
    assert json.loads((tmp_path / "piloto.json").read_text(encoding="utf-8")) == {"original": True}
    assert (tmp_path / "piloto_p3v2.jsonl").exists() and len((tmp_path / "piloto_p3v2.jsonl").read_text(encoding="utf-8").splitlines()) == 5
    assert r["projecao_rodada_completa_usd"] == pytest.approx(60 * (r["custo_medio_usd"] + ex.CUSTO_P1_ESTIMADO))


def test_piloto_do_p3_v2_que_falha_nao_projeta_rodada(tmp_path):
    cli, _ = cliente_falso(tmp_path, Falso(erro_em=3))
    r = ex.executar_piloto_p3v2(cli, pasta=tmp_path)
    assert r["erro"] and r["chamadas"] == 2 and r["projecao_rodada_completa_usd"] is None


def test_analise_compara_o_e6_com_o_e4_encadeado_ja_medido(tmp_path):
    r = ab.resumir_tudo(tmp_path / "vazio", tmp_path / "sem_piloto")
    assert r["variantes"]["E6/encadeado_v2"] == {"medido": False} and r["comparacoes"]["E6"]["medido"] is False
    cli, _ = cliente_falso(tmp_path)
    for exp, var in [("E4", "encadeado"), ("E6", "encadeado_v2")]:
        ex.executar_variante(cli, exp, var, pasta=tmp_path / "brutos")
    r = ab.resumir_tudo(tmp_path / "brutos", tmp_path / "sem_piloto")
    c = r["comparacoes"]["E6"]
    assert c["base"] == "encadeado_v1" and c["alternativa"] == "encadeado_v2" and c["casos_comparados"] == 20
    assert c["diferenca_acerto_pp"] == 0 and r["variantes"]["E6/encadeado_v2"]["chamadas_por_resposta"] == 2
    assert "Encadeado com e-mail v2" in ab.relatorio(r)


def test_rodada_do_e6_exige_o_piloto_do_p3_v2(tmp_path, monkeypatch):
    monkeypatch.setattr(ex, "PILOTO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["rodar_biblioteca.py", "--completo", "--so", "E6"])
    with pytest.raises(SystemExit) as e:
        rb.main()
    assert "--piloto-e6" in str(e.value)
    (tmp_path / "piloto_p3v2.json").write_text(json.dumps({"projecao_rodada_completa_usd": None}), encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        rb.main()
    assert "não terminou" in str(e.value)


def test_completo_sem_so_nao_roda_o_e6(tmp_path, monkeypatch):
    chamados = []
    monkeypatch.setattr(ex, "PILOTO", tmp_path)
    (tmp_path / "piloto.json").write_text(json.dumps({"projecao_rodada_completa_usd": 0.01}), encoding="utf-8")
    monkeypatch.setattr(ex, "executar_variante", lambda cli, exp, var, **k: chamados.append((exp, var)) or (0, 0, None))
    monkeypatch.setattr(sys, "argv", ["rodar_biblioteca.py", "--completo"])
    monkeypatch.setattr(ex, "ControleBiblioteca", lambda: type("C", (), {"gasto": 0.0})())
    monkeypatch.setattr(rb, "ClienteAnthropic", lambda ctl: object())
    rb.main()
    assert ("E6", "encadeado_v2") not in chamados and len(chamados) == len(ex.ORDEM) - 1
