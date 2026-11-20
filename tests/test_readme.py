from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _primeira_tabela(texto):
    linhas = []
    for l in texto.splitlines():
        if l.startswith("|"):
            linhas.append(l)
        elif linhas:
            break
    return linhas


def test_tabela_do_readme_e_a_do_relatorio():
    rel = _primeira_tabela((RAIZ / "resultados" / "RELATORIO.md").read_text(encoding="utf-8"))
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert rel and all(l in readme for l in rel), "tabela do README difere de resultados/RELATORIO.md"


def test_readme_declara_as_limitacoes_obrigatorias():
    t = (RAIZ / "README.md").read_text(encoding="utf-8")
    for frase in ["Só 50 casos por rodada", "Um modelo só", "gabarito foi criado pelo autor do projeto", "Sem temperatura 0", "não generalizáveis", "A v2 foi desenhada depois de ver a v1"]:
        assert frase in t, frase


def test_tabela_v2_do_readme_e_a_do_relatorio_v2():
    p = RAIZ / "resultados" / "v2" / "RELATORIO.md"
    rel = _primeira_tabela(p.read_text(encoding="utf-8"))
    assert rel and all(l in (RAIZ / "README.md").read_text(encoding="utf-8") for l in rel)


def test_readme_traz_numeros_da_iteracao():
    import json
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent
    it = json.loads((raiz / "resultados/v2/iteracao.json").read_text(encoding="utf-8"))
    readme = (raiz / "README.md").read_text(encoding="utf-8")
    pc = lambda x: f"{100 * x:.1f}".replace(".", ",") + "%"
    assert pc(it["acerto_v1"]) in readme and pc(it["acerto_v2"]) in readme
    assert f"p = {it['p_sinal']:.3f}".replace(".", ",") in readme
    vt = it["por_tipo"]["valor_total"]
    assert f"{vt['certas_v1']} de {vt['respostas']}" in readme
    assert f"{vt['certas_v2']} de {vt['respostas_v2']}" in readme
    assert f"{it['custo_v2']:.6f}".replace(".", ",") in readme
    assert "regra do T4 v2 foi escrita depois de ver os erros" in readme
