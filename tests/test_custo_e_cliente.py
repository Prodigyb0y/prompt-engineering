import json

import pytest

import cliente as c
from custo import carregar_precos, custo_usd

PRECOS = carregar_precos()


def test_precos_registrados_com_fonte_e_data():
    assert PRECOS["modelo"] == "claude-haiku-5-5"
    assert PRECOS["consultado_em"] and PRECOS["fonte"].startswith("https://")


def test_conta_de_custo():
    # 1.000.000 tokens de entrada + 1.000.000 de saída na faixa até 100k de prompt: 0,10 + 0,50
    assert custo_usd(1_000, 0, PRECOS) == pytest.approx(0.0001)
    assert custo_usd(0, 1_000, PRECOS) == pytest.approx(0.0005)
    assert custo_usd(500, 200, PRECOS) == pytest.approx(500 * 0.10e-6 + 200 * 0.50e-6)
    assert custo_usd(200_000, 0, PRECOS) == pytest.approx(200_000 * 0.50e-6)  # faixa acima de 100k


def falso(resp="{}", tin=100, tout=50):
    return lambda s, u, m: {"texto": resp, "tokens_entrada": tin, "tokens_saida": tout}


def test_chamada_registra_custo_latencia_e_gasto(tmp_path):
    ctl = c.ControleCusto(tmp_path / "gasto.json")
    cli = c.ClienteAnthropic(ctl, PRECOS, enviar=falso(tin=1000, tout=100))
    r = cli.chamar("", "oi", 300)
    assert r["custo_usd"] == pytest.approx(1000 * 0.10e-6 + 100 * 0.50e-6)
    assert r["latencia_s"] >= 0 and r["tentativas"] == 1
    assert json.loads((tmp_path / "gasto.json").read_text())["gasto_usd"] == pytest.approx(r["custo_usd"])


def test_teto_bloqueia_antes_de_chamar(tmp_path):
    (tmp_path / "gasto.json").write_text(json.dumps({"gasto_usd": 0.99999}))
    chamadas = []
    cli = c.ClienteAnthropic(c.ControleCusto(tmp_path / "gasto.json"), PRECOS,
                             enviar=lambda *a: chamadas.append(1) or falso()(*a))
    with pytest.raises(c.TetoExcedido):
        cli.chamar("", "x" * 4000, 800)
    assert chamadas == []                      # não chegou a chamar a API
    assert "teto excedido" in (tmp_path / "erros.log").read_text()


def test_reserva_usa_custo_maximo(tmp_path):
    # gasto + reserva > teto mesmo com gasto pequeno: bloqueia
    ctl = c.ControleCusto(tmp_path / "g.json", teto=0.0001)
    cli = c.ClienteAnthropic(ctl, PRECOS, enviar=falso())
    with pytest.raises(c.TetoExcedido):
        cli.chamar("", "oi", 800)              # reserva ~ 800 * 0,5e-6 = 0,0004 > 0,0001


class ErroTransitorio(Exception):
    status_code = 529


class ErroPermanente(Exception):
    status_code = 400


def test_retry_so_em_erro_transitorio(tmp_path):
    n = {"v": 0}

    def instavel(s, u, m):
        n["v"] += 1
        if n["v"] < 3:
            raise ErroTransitorio()
        return {"texto": "ok", "tokens_entrada": 10, "tokens_saida": 5}

    cli = c.ClienteAnthropic(c.ControleCusto(tmp_path / "g.json"), PRECOS, enviar=instavel, dormir=lambda s: None)
    assert cli.chamar("", "oi", 100)["tentativas"] == 3


def test_desiste_depois_de_3_tentativas(tmp_path):
    n = {"v": 0}

    def sempre(s, u, m):
        n["v"] += 1
        raise ErroTransitorio()

    cli = c.ClienteAnthropic(c.ControleCusto(tmp_path / "g.json"), PRECOS, enviar=sempre, dormir=lambda s: None)
    with pytest.raises(ErroTransitorio):
        cli.chamar("", "oi", 100)
    assert n["v"] == c.MAX_TENTATIVAS


def test_erro_permanente_nao_repete(tmp_path):
    n = {"v": 0}

    def ruim(s, u, m):
        n["v"] += 1
        raise ErroPermanente()

    cli = c.ClienteAnthropic(c.ControleCusto(tmp_path / "g.json"), PRECOS, enviar=ruim, dormir=lambda s: None)
    with pytest.raises(ErroPermanente):
        cli.chamar("", "oi", 100)
    assert n["v"] == 1


def test_sem_chave_falha_sem_imprimir_nada(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(c, "carregar_env", lambda *a, **k: None)
    cli = c.ClienteAnthropic(c.ControleCusto(tmp_path / "g.json"), PRECOS)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        cli.chamar("", "oi", 100)


def test_nenhuma_chave_no_repositorio():
    import re
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent
    padrao = re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")
    for arq in raiz.rglob("*"):
        if arq.is_file() and ".git" not in arq.parts and arq.suffix in {".py", ".json", ".md", ".txt", ".html", ".example", ""}:
            assert not padrao.search(arq.read_text(encoding="utf-8", errors="ignore")), f"possível chave em {arq}"


def test_rodar_grava_bruto_e_retoma(tmp_path):
    import json as j
    import rodar
    casos = j.loads((rodar.RAIZ / "dados" / "casos_teste.json").read_text(encoding="utf-8"))
    gab = j.loads((rodar.RAIZ / "dados" / "gabarito.json").read_text(encoding="utf-8"))
    chamadas = []

    def eco(system, user, m):
        chamadas.append(1)
        return {"texto": "não é json", "tokens_entrada": 100, "tokens_saida": 10}

    cli = c.ClienteAnthropic(c.ControleCusto(tmp_path / "g.json"), PRECOS, enviar=eco)
    feitas, novas = rodar.executar("piloto", cli, casos, gab, tmp_path / "b")
    assert (feitas, novas) == (0, 10) and len(chamadas) == 10          # 5 casos x T1,T4 x 1 rep
    reg = j.loads(next((tmp_path / "b").glob("T1_*_r1.json")).read_text(encoding="utf-8"))
    assert reg["prompt_hash12"] and reg["avaliacao"]["json_valido"] is False and reg["custo_usd"] > 0
    assert rodar.executar("piloto", cli, casos, gab, tmp_path / "b") == (10, 0)   # retomável: não repete
    assert len(chamadas) == 10
    _, tecs, reps = rodar.selecionar("completo", casos)
    assert tecs == ["T1", "T2", "T3", "T4"] and reps == 3 and len(casos) * len(tecs) * reps == 600
