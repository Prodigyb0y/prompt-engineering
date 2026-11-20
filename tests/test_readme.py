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
