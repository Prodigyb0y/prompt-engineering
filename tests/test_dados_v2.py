import hashlib
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
V2 = RAIZ / "dados" / "v2"


def test_validacao_v2_passa():
    r = subprocess.run([sys.executable, str(RAIZ / "src" / "validar_dados_v2.py")], capture_output=True, text=True,
                       cwd=RAIZ / "src")
    assert r.returncode == 0, r.stdout + r.stderr


def test_v2_congelada():
    for linha in (V2 / "CONGELADO.sha256").read_text().splitlines():
        esperado, nome = linha.split()
        conteudo = (V2 / nome).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(conteudo).hexdigest() == esperado, f"{nome} (v2) mudou depois do congelamento"


def test_v2_sem_artefato_e_com_tipos_novos():
    casos = json.loads((V2 / "casos_teste.json").read_text(encoding="utf-8"))
    assert len(casos) == 50 and not any("Ltda." in c["texto"] for c in casos)
    tipos = {c["tipo"] for c in casos}
    assert {"correcao", "valor_total", "numero_extenso", "moeda_extenso", "email_longo"} <= tipos


def test_v2_nao_repete_v1_nem_fewshot():
    v2 = {c["texto"] for c in json.loads((V2 / "casos_teste.json").read_text(encoding="utf-8"))}
    v1 = {c["texto"] for c in json.loads((RAIZ / "dados" / "casos_teste.json").read_text(encoding="utf-8"))}
    fs = {e["entrada"] for e in json.loads((RAIZ / "dados" / "exemplos_fewshot.json").read_text(encoding="utf-8"))}
    assert not (v2 & v1) and not (v2 & fs)


def test_geracao_v2_e_deterministica(tmp_path, monkeypatch):
    import gerar_dados_v2 as g2
    monkeypatch.setattr(g2, "SAIDA", tmp_path)
    g2.main()
    for nome in ["casos_teste.json", "gabarito.json"]:
        assert (tmp_path / nome).read_bytes().replace(b"\r\n", b"\n") == (V2 / nome).read_bytes().replace(b"\r\n", b"\n")


def test_prompts_continuam_os_da_v1():
    """A v2 muda só os casos: os hashes dos prompts não podem mudar."""
    esperados = {"T1": "1ef67d6a52fc", "T2": "be0e8998a563", "T3": "b3a7a7a94ceb", "T4": "bb14abcde430"}
    import prompts_lib as p
    assert {d["id"]: p.hash_prompt(d["system"], d["user_template"]) for d in p.definicoes() if d["versao"] == "v1"} == esperados


def test_caminhos_por_versao(monkeypatch):
    import importlib

    import caminhos
    monkeypatch.setenv("PE_VERSAO", "v2")
    c2 = importlib.reload(caminhos)
    assert c2.DADOS == RAIZ / "dados" / "v2" and c2.RESULTADOS == RAIZ / "resultados" / "v2"
    monkeypatch.delenv("PE_VERSAO")
    c1 = importlib.reload(caminhos)
    assert c1.DADOS == RAIZ / "dados" and c1.RESULTADOS == RAIZ / "resultados"
