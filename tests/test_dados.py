import hashlib
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"


def test_validacao_do_gabarito_passa():
    r = subprocess.run([sys.executable, str(RAIZ / "src" / "validar_dados.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_arquivos_congelados_nao_mudaram():
    for linha in (DADOS / "CONGELADO.sha256").read_text().splitlines():
        esperado, nome = linha.split()
        assert hashlib.sha256((DADOS / nome).read_bytes()).hexdigest() == esperado, f"{nome} mudou depois do congelamento"


def test_50_casos_e_gabarito_completo():
    casos = json.loads((DADOS / "casos_teste.json").read_text(encoding="utf-8"))
    gab = json.loads((DADOS / "gabarito.json").read_text(encoding="utf-8"))
    assert len(casos) == 50 and {c["id"] for c in casos} == set(gab)
    assert all("tipo" in c and c["texto"] for c in casos)


def test_geracao_e_deterministica(tmp_path, monkeypatch):
    import gerar_dados
    monkeypatch.setattr(gerar_dados, "DADOS", tmp_path)
    gerar_dados.main()
    for nome in ["casos_teste.json", "gabarito.json", "exemplos_fewshot.json"]:
        assert (tmp_path / nome).read_bytes() == (DADOS / nome).read_bytes(), f"{nome} não é reproduzível com seed 42"
