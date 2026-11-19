import json
import re

import pytest

import gerar_demo as gd

# os resultados brutos não vão para o Git: sem eles, estes testes são pulados
sem_brutos = pytest.mark.skipif(not list((gd.RAIZ / "resultados" / "brutos").glob("T*.json")), reason="sem resultados brutos locais")


@sem_brutos
def test_demo_gerada_a_partir_dos_resultados(tmp_path, monkeypatch):
    monkeypatch.setattr(gd, "RAIZ", gd.RAIZ)  # usa os resultados reais do repositório
    d = gd.montar_dados()
    assert len(d["casos"]) == 50 and len(d["resumo"]) == 4 and d["repeticoes"] == 3
    assert all(len(c["saidas"]) == 4 for c in d["casos"])
    resumo = json.loads((gd.RAIZ / "resultados" / "resumo.json").read_text(encoding="utf-8"))
    for linha in d["resumo"]:
        assert linha["acerto"] == resumo[linha["id"]]["acerto_caso_media"]   # número vem do arquivo, não digitado


@sem_brutos
def test_html_embute_json_valido_sem_fechar_script():
    gd.main()
    html = (gd.RAIZ / "docs" / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<script id="dados" type="application/json">(.*?)</script>', html, re.DOTALL)
    assert json.loads(m.group(1).replace("<\\/", "</"))["casos"]
    assert "innerHTML" not in html and "http://" not in html and "https://" not in html  # sem recursos externos
