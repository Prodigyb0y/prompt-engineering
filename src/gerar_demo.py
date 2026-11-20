"""Gera docs/index.html (página estática única, sem servidor, sem chave e sem CDN) a partir de resultados/resumo.json.

Nenhum número é digitado à mão: tudo vem do resumo (que vem dos arquivos de resultado). O modelo da página
(HTML, CSS e JS) fica em src/demo_modelo.html; este script só injeta os dados.

Uso: python src/gerar_demo.py
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MODELO = Path(__file__).resolve().parent / "demo_modelo.html"
RESUMO = RAIZ / "resultados" / "resumo.json"
SAIDA = RAIZ / "docs" / "index.html"
MARCADOR = "/*__DADOS__*/"
LIMITE_BYTES = 1_000_000


def dados_da_pagina(resumo):
    """O que vai embutido na página: tudo do resumo, menos o que só serve ao apêndice (variantes detalhadas)."""
    d = {k: v for k, v in resumo.items() if k in ("projeto", "custo", "prompts", "experimentos", "playground", "como_medi", "partes_legenda")}
    d["experimentos"] = [{k: v for k, v in e.items() if k not in ("variantes", "comparacao", "tecnicas")} for e in d["experimentos"]]
    return d


def gerar(resumo=None, saida=SAIDA, modelo=MODELO):
    resumo = resumo or json.loads(RESUMO.read_text(encoding="utf-8"))
    dados = json.dumps(dados_da_pagina(resumo), ensure_ascii=False, separators=(",", ":"))
    dados = dados.replace("</", "<\\/").replace("<!--", "<\\!--")   # nada dentro do JSON pode fechar a tag <script>
    html = modelo.read_text(encoding="utf-8")
    assert html.count(MARCADOR) == 1
    html = html.replace(MARCADOR, dados)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(html, encoding="utf-8", newline="\n")
    return len(html.encode("utf-8"))


def main():
    n = gerar()
    print(f"docs/index.html gerado: {n / 1024:.0f} KB" + ("" if n < LIMITE_BYTES else f" (acima de {LIMITE_BYTES // 1000} KB!)"))


if __name__ == "__main__":
    main()
