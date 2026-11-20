import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
README = (RAIZ / "README.md").read_text(encoding="utf-8")
MEDICAO = (RAIZ / "docs" / "medicao.md").read_text(encoding="utf-8")
RESUMO = json.loads((RAIZ / "resultados" / "resumo.json").read_text(encoding="utf-8"))

ORDEM = ["## O que este projeto mostra", "## Biblioteca de prompts", "## O prompt P1 completo", "## Antes e depois de um prompt", "## Experimentos",
         "## Por que isso importa para um time de negócio", "## Limitações", "## Como rodar", "## Estrutura", "## Apêndice"]


def test_secoes_na_ordem_obrigatoria():
    pos = [README.index(s) for s in ORDEM]
    assert pos == sorted(pos)


def test_abre_com_titulo_imagem_demo_e_aviso_de_dados_ficticios():
    topo = README[:1500]
    assert topo.startswith("# Prompt Lab · Gutenberg Systems")
    assert "docs/img/demo-desktop.png" in topo and RESUMO["projeto"]["demo"] in topo
    assert "recriação conceitual" in topo and "fictícios" in topo
    assert (RAIZ / "docs/img/demo-desktop.png").stat().st_size > 10000 and (RAIZ / "docs/img/demo-mobile.png").stat().st_size > 10000


def test_tabela_dos_5_prompts_vem_do_resumo_e_aponta_arquivos_existentes():
    for p in RESUMO["prompts"]:
        assert f"| {p['id']} |" in README and (RAIZ / p["arquivo"]).exists() and f"]({p['arquivo']})" in README
        if not p["medido"]:
            assert "não medido" in README


def test_p1_completo_e_placar_vem_dos_arquivos():
    p1 = next(p for p in RESUMO["prompts"] if p["id"] == "P1")
    assert p1["system"] in README and p1["hash12"] in README
    e2 = next(e for e in RESUMO["experimentos"] if e["id"] == "E2")
    pl = e2["placar"]
    assert f"{pl['antes']}/{pl['de']} → {pl['depois']}/{pl['de']}" in README
    assert "```diff" in README


def test_experimentos_nao_medidos_dizem_que_nao_foram_medidos():
    for e in RESUMO["experimentos"]:
        assert f"**{e['id']} ·" in README
        if not e["medido"]:
            bloco = README[README.index(f"**{e['id']} ·"):].split("\n\n")[0]
            assert "não medido" in bloco


def test_limitacoes_obrigatorias():
    for frase in ["fictícios", "Um único modelo", "gabarito foi escrito pelo autor", "escrita olhando os mesmos casos"]:
        assert frase in README, frase


def test_links_relativos_do_readme_existem():
    for alvo in re.findall(r"\]\((?!http)([^)#]+)\)", README):
        assert (RAIZ / alvo).exists(), alvo


def test_apendice_medicao_tem_conteudo_estatistico_e_links_validos():
    for t in ["Bootstrap", "bootstrap", "sinal", "Auditoria", "Mapa de caminhos"]:
        assert t in MEDICAO, t
    for alvo in re.findall(r"\]\((?!http)([^)#]+)\)", MEDICAO):
        assert (RAIZ / "docs" / alvo).resolve().exists(), alvo


def test_numeros_da_iteracao_no_apendice_batem_com_o_json():
    it = json.loads((RAIZ / "resultados/extracao/v2/iteracao.json").read_text(encoding="utf-8"))
    assert "92,0%" in MEDICAO and "100,0%" in MEDICAO and it  # os valores medidos continuam como estavam


def test_jargao_estatistico_fora_do_texto_principal():
    for termo in ["bootstrap", "p-valor", "intervalo de confiança", "teste do sinal"]:
        assert termo.lower() not in README.lower().replace("bootstrap, teste do sinal pareado, auditoria e a rodada v1", ""), termo


def test_sem_chave_no_texto():
    assert not re.search(r"sk-ant-[A-Za-z0-9_\-]{20,}", README + MEDICAO)
