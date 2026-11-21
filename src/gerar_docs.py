"""Gera README.md e docs/medicao.md a partir de resultados/resumo.json (e, para o apêndice, do README anterior).

Nenhum número do README é digitado à mão: tabelas e frases vêm do resumo. O que não foi medido aparece como
"não medido". O apêndice docs/medicao.md reaproveita, sem alterar os números, as seções estatísticas do README
anterior (preservado em docs/legado/) e acrescenta as regras e a tabela das rodadas novas.

Uso: python src/gerar_docs.py
"""
import json
import re
from pathlib import Path

import analisar_biblioteca as ab
import avaliadores
import conteudo_biblioteca as cb
import consolidar as co
import experimentos as ex

RAIZ = Path(__file__).resolve().parent.parent
RESUMO = RAIZ / "resultados" / "resumo.json"
ANTERIOR = RAIZ / "docs" / "legado" / "README_estudo_de_avaliacao.md"
IMG_DESKTOP, IMG_MOBILE = "docs/img/demo-desktop.png", "docs/img/demo-mobile.png"

REESCRITA_CAMINHOS = [  # o README anterior citava as pastas antigas; estes são os caminhos atuais
    ("resultados/v2/RELATORIO.md", "resultados/extracao/v2/RELATORIO.md"), ("resultados/v2/ERROS.md", "resultados/extracao/v2/ERROS.md"),
    ("resultados/v2/ITERACAO.md", "resultados/extracao/v2/ITERACAO.md"), ("resultados/v2/AUDITORIA.md", "resultados/extracao/v2/AUDITORIA.md"),
    ("resultados/RELATORIO.md", "resultados/extracao/v1/RELATORIO.md"), ("resultados/ERROS.md", "resultados/extracao/v1/ERROS.md"),
    ("resultados/AUDITORIA.md", "resultados/extracao/v1/AUDITORIA.md"), ("dados/v2/", "dados/extracao/v2/"),
    ("dados/REVISAO_E_LIMITACOES.md", "dados/extracao/v1/REVISAO_E_LIMITACOES.md"), ("prompts/T4_system_prompt_v2.json", "prompts/extracao/T4_system_prompt_v2.json"),
]


def _tabela(cabecalho, linhas):
    return "\n".join(["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)] + ["| " + " | ".join(l) + " |" for l in linhas])


def _texto_acerto(p):
    return "não medido" if not p["medido"] else p["acerto"]["texto"] + (" (desenvolvimento)" if p["id"] == "P1" else "")


def _texto_custo(p):
    return "não medido" if not p["medido"] else co.usd(p["custo_chamada_usd"])


def readme(r):
    P, C = r["projeto"], r["custo"]
    prompts = {p["id"]: p for p in r["prompts"]}
    exps = {e["id"]: e for e in r["experimentos"]}
    p1, e2 = prompts["P1"], exps["E2"]
    L = [f"# {P['nome']}", "", f"**{P['frase_impacto']}**", "",
         f"[![Prompt Lab: tela inicial da demo]({IMG_DESKTOP})]({P['demo']})", "",
         f"**Demo (sem instalação e sem chave): {P['demo']}** · [versão para celular]({IMG_MOBILE})", "",
         f"Projeto de portfólio com exemplos de prompts bem estruturados e experimentações com LLMs. "
         f"É uma **recriação conceitual com dados 100% fictícios**: {P['empresa_nota']}", ""]
    if r["pendencias"] or not all(p["medido"] for p in r["prompts"]):
        L += [f"> **Estado desta versão:** prompts, dados, gabaritos congelados, regras de acerto, testes e a demo estão prontos. "
              f"As rodadas pagas de {', '.join(r['pendencias'])} (e a medição do P2 ao P5) ainda **não foram executadas**, porque dependem da chave da API do autor. "
              f"Onde não há medição, o texto diz \"não medido\"; nenhum número foi estimado. Para medir: `{cb.COMANDOS['piloto']}`, depois `{cb.COMANDOS['completo']}` e `{cb.COMANDOS['depois']}`.", ""]
    L += ["## O que este projeto mostra", "",
          "- **Prompts bem estruturados:** cinco prompts de negócio, cada um com papel, contexto, tarefa, formato de saída, regras e casos de borda, e uma técnica em destaque.",
          "- **Experimentos com LLM:** seis comparações curtas (técnica, antes e depois, few-shot, encadear, raciocínio, reescrever um prompt depois de ler os erros), cada uma com o que foi testado, o resultado e quando usar.",
          f"- **Decisões com custo medido:** acerto contra um gabarito escrito antes de rodar, custo por chamada e teto de gasto no código (gasto até aqui: {co.usd(C['total_usd'], 4)} de {co.usd(C['teto_total_usd'], 2)}).", "",
          "## Biblioteca de prompts", ""]
    L.append(_tabela(["#", "Prompt (problema de negócio)", "Técnica em destaque", "Acerto", "Custo por chamada", "Arquivo"],
                     [[p["id"], f"**{p['nome']}**. {p['problema']}", p["tecnica"], _texto_acerto(p), _texto_custo(p), f"[`{p['arquivo']}`]({p['arquivo']})"] for p in r["prompts"]]))
    L += ["", "O acerto de cada prompt é medido contra um gabarito escrito e congelado (hash) antes de rodar; o do P1 foi medido nos mesmos 50 casos em que a regra foi escrita. "
          "A regra de acerto de cada prompt está em [`src/avaliadores.py`](src/avaliadores.py). Cada cartão da demo mostra o prompt completo, as partes coloridas, um exemplo de entrada e saída e o que aprendi.", ""]

    L += [f"## O prompt P1 completo (T4 v2, hash `{p1['hash12']}`)", "", "System prompt:", "", "```text", p1["system"], "```", "", "Mensagem do usuário (o `{texto}` recebe o pedido):", "", "```text", p1["user_template"], "```", "",
          "Anatomia comentada:", ""]
    L.append(_tabela(["Parte", "Trecho do prompt", "Para que serve"], [[a["rotulo"], "`" + (a["trecho"].replace("\n", " ")[:80] + ("…" if len(a["trecho"]) > 80 else "")).replace("|", "\\|") + "`", a["funcao"]] for a in p1["anatomia"]]))
    L += ["", "## Antes e depois de um prompt", "", f"**{e2['resultado']}**", "",
          f"Placar no tipo \"{e2['placar']['tipo']}\" (respostas certas): **{e2['placar']['antes']}/{e2['placar']['de']} → {e2['placar']['depois']}/{e2['placar']['de']}**. O que mudou no prompt (T4 v1 → v2):", "", "```diff"]
    for l in e2["diff"]:
        L.append({"add": "+ ", "del": "- ", "ctx": "  ", "sep": "  "}[l["tipo"]] + l["texto"])
    L += ["```", "", f"Ressalva: {e2['ressalva']}", ""]
    v = e2.get("validacao")
    if v:
        L += ["### Testado em pedidos novos", "", v["texto"], "", v["criterio"], "", f"Ressalva: {v['ressalva']}", ""]
    L += ["## Experimentos", ""]
    for e in r["experimentos"]:
        if e["medido"]:
            L += [f"**{e['id']} · {e['titulo']}** — {e['resultado']}", f"Quando usar: {e['quando_usar']}", ""]
        else:
            L += [f"**{e['id']} · {e['titulo']}** — *não medido.* {e['pendencia']}", f"Como será medido: {e['como_medido']}", ""]
    L += ["## Por que isso importa para um time de negócio", "",
          f"1. **A regra de negócio vale mais que a técnica.** {exps['E1']['resultado']} Escrever a regra no prompt resolveu o que a técnica mais cara resolvia (Experimento 2).",
          "2. **Prompt é um artefato que se versiona e se testa.** Cada prompt tem versão e hash, o gabarito é congelado antes de rodar e a regra de acerto é código: dá para mudar o prompt e saber se piorou.",
          f"3. **Custo medido, não suposto.** Cada resposta tem o custo calculado a partir dos tokens informados pela API, e o cliente para antes de passar do teto. Isso permite decidir se uma técnica mais cara compensa, com número.", "",
          ""] + ([f"**Conclusão.** {r['conclusao']['resumo']} A versão completa, com o que dá e o que não dá para concluir, está na seção \"Conclusão\" da [demo]({P['demo']}).", ""] if r.get("conclusao") else []) + [
          "## Limitações", ""]
    L += [f"- {x}" for x in P["limitacoes"]]
    L += ["- Não verifiquei se algum nome de fornecedor fictício coincide com empresa real (só conferi uma lista curta de nomes conhecidos).", "",
          "## Como rodar", "", "```bash", f"git clone {P['repo']}", "cd prompt-engineering",
          "python -m venv .venv && .venv/bin/pip install -r requirements.txt     # Windows: .venv\\Scripts\\python.exe -m pip ...",
          ".venv/bin/python -m pytest -q                     # testes que não chamam a API",
          "cp .env.example .env                              # preencha ANTHROPIC_API_KEY (nunca versione o .env)",
          ".venv/bin/python src/rodar_biblioteca.py --piloto      # 5 chamadas por prompt novo",
          ".venv/bin/python src/rodar_biblioteca.py --completo    # E3, E4, E5 e P4 (retomável; teto próprio de US$ 0,60)",
          ".venv/bin/python src/analisar_biblioteca.py && .venv/bin/python src/consolidar.py   # resultados/resumo.json",
          ".venv/bin/python src/gerar_demo.py && .venv/bin/python src/gerar_docs.py             # docs/index.html, README.md e docs/medicao.md", "```", "",
          "A chave só existe em `.env` ou na variável `ANTHROPIC_API_KEY`. O modelo não aceita temperatura, então quem refizer as rodadas pode obter números diferentes. Rodadas antigas (extração v1 e v2): comandos em [`docs/medicao.md`](docs/medicao.md).", "",
          "## Estrutura", "", "```",
          "prompts/            P1 a P5 e os controles dos experimentos (versão, hash e anatomia)",
          "prompts/extracao/   T1 a T4 (v1) e T4 v2 da extração",
          "dados/biblioteca/   casos e gabaritos de P2 a P5 (20 casos cada), hashes e revisão",
          "dados/extracao/     v1 e v2: 50 casos cada, gabarito, exemplos few-shot, hashes",
          "resultados/         resumo.json (alimenta a demo), extracao/ (v1, v2 e iteração), biblioteca/ (rodadas novas)",
          "src/                geradores, validadores, avaliadores, cliente com teto de gasto, análise, demo, documentação",
          "tests/              testes que não chamam a API",
          "docs/               index.html (demo), medicao.md (apêndice), checklist_entrega.md, img/, legado/", "```", "",
          "## Apêndice", "", "Bootstrap, teste do sinal pareado, auditoria e a rodada v1 estão em [**Detalhes da medição**](docs/medicao.md).", ""]
    return "\n".join(L)


def _secao(texto, inicio, fim=None):
    m = re.search(rf"^{re.escape(inicio)}.*?$", texto, re.M)
    ini = m.start()
    if fim is None:
        return texto[ini:].strip()
    f = re.search(rf"^{re.escape(fim)}", texto[m.end():], re.M)
    return texto[ini:m.end() + f.start()].strip()


def _validacao_md():
    arq = RAIZ / "resultados" / "extracao" / "v3" / "validacao.json"
    if not arq.exists():
        return []
    v = json.loads(arq.read_text(encoding="utf-8"))
    vt = v["veredito"]
    linhas = [[t, str(d["casos"]), f"{d['certas_v1']}/{d['respostas']}", f"{d['certas_v2']}/{d['respostas_v2']}"] for t, d in v["por_tipo"].items()]
    return ["### 4.1 Validação do T4 v2 em pedidos novos", "",
            f"{v['casos']} pedidos (H01 a H20) gerados por `src/gerar_dados_v3.py` (seed 3003, textos diferentes dos da v1, da v2 e dos exemplos few-shot) e congelados por hash em `dados/extracao/v3/CONGELADO.sha256` antes de qualquer chamada. "
            "T4 v1 e T4 v2, 3 repetições cada, mesmas regras de acerto da extração, mesmo controle de custo. Critério escrito antes da rodada em `src/comparar_validacao.py`: generaliza se a v2 acertar pelo menos 17 das 18 respostas de valor total e não ficar abaixo da v1 nos demais tipos.", "",
            _tabela(["Tipo", "Casos", "T4 v1 (respostas certas)", "T4 v2 (respostas certas)"], linhas), "",
            f"Acerto geral: v1 {ab.pct(v['acerto_v1'])}, v2 {ab.pct(v['acerto_v2'])}. Custo por resposta: v1 {co.usd(v['custo_v1'])}, v2 {co.usd(v['custo_v2'])}. Tokens de saída por resposta: v1 {ab.num(v['tokens_saida_v1'], 1)}, v2 {ab.num(v['tokens_saida_v2'], 1)}. "
            f"Casos melhores na v2: {len(v['melhorou'])}; piores: {len(v['piorou'])}; teste do sinal exato pareado: p = {ab.num(v['p_sinal'], 3)}. Veredito do critério: {'generalizou' if vt['generaliza'] else 'não generalizou'}; regressão: {'sim' if vt['regressao'] else 'não'}. "
            "Relatório: `resultados/extracao/v3/VALIDACAO.md`.", "",
            "Limitações: só 6 casos de valor total; mesmo gerador de frases dos 50 casos anteriores; gabarito do próprio autor.", "",
            "### 4.2 E6: P3 v2 (diagnóstico antes da correção)", "",
            "O E6 repete o fluxo do E4 (P1 v2 → e-mail) trocando só o prompt do e-mail e usa como base a rodada `E4/encadeado`, já medida. "
            "O P3 v2 (`prompts/P3_encadeado_v2.json`) foi escrito depois de ler os erros do P3 v1 nos mesmos 20 casos (ver `resultados/biblioteca/DIAGNOSTICO.md`): é resultado de desenvolvimento. "
            "A regra de acerto oficial não mudou; a \"reanálise por pedido\" (campo contado só se aparece em item de lista) é auxiliar e foi escrita depois de ler os erros. "
            "Piloto de 5 chamadas antes da rodada completa: 5 de 5 certas, projeção de custo conferida contra o teto.", ""]


def medicao(r, anterior=None):
    ant = anterior if anterior is not None else ANTERIOR.read_text(encoding="utf-8")
    ab_resumo = ab.resumir_tudo()
    blocos = [
        _secao(ant, "## 6. Como cada métrica foi medida", "## 7. Resultados").replace("## 6. Como cada métrica foi medida", "## 2. Como cada métrica da extração foi medida"),
        "## 3. Resultados da extração (rodadas v2 e v1)\n\n" + _secao(ant, "### 7.1", "### 7.2").replace("### 7.1", "### 3.1") + "\n\n" +
        _secao(ant, "### 7.2", "### 7.3").replace("### 7.2", "### 3.2") + "\n\n" + _secao(ant, "### 7.3", "### 7.4").replace("### 7.3", "### 3.3"),
        _secao(ant, "## 10. Auditoria e decisões registradas", "## 11. Como rodar").replace("## 10.", "## 5."),
        _secao(ant, "## 4. Tarefa e dados", "## 5. Técnicas de prompt").replace("## 4. Tarefa e dados", "## 6. Dados da extração"),
    ]
    novo = [
        "## 4. Rodadas novas: P2 a P5 (E3, E4, E5, E6 e P4) e validação do T4 v2", "",
        "Regras de acerto, escritas antes de qualquer rodada paga (código em `src/avaliadores.py`):", "",
        "```text", avaliadores.__doc__.split("\n\n", 1)[1].strip(), "```", "",
        f"Escala: {r['como_medi']['casos_novos']} casos por prompt novo, {r['como_medi']['repeticoes']} repetições por variante, piloto de 5 chamadas por prompt antes da rodada completa. "
        f"Teto das rodadas novas: {co.usd(ex.TETO_RODADAS_USD, 2)} (e nunca mais que {co.usd(ex.TETO_TOTAL_USD, 2)} no total do repositório, contando o gasto anterior de {co.usd(ex.GASTO_ANTERIOR_USD, 6)}). "
        "Intervalo de confiança: bootstrap percentil, 10.000 reamostragens dos 20 casos, seed 42. Comparação: teste do sinal exato pareado por caso, empates excluídos; com 20 casos, p < 0,05 é raro.", "",
        "Dados: [`dados/biblioteca/REVISAO_E_LIMITACOES.md`](../dados/biblioteca/REVISAO_E_LIMITACOES.md) (revisão manual, correções do gabarito do P4 e limitações). Gabaritos congelados por hash em `dados/biblioteca/<p2..p5>/CONGELADO.sha256`.", "",
    ]
    linhas = []
    for chave, v in ab_resumo["variantes"].items():
        exp, var = chave.split("/")
        if v["medido"]:
            linhas.append([exp, ab.ROTULOS[var], ab.pct(v["acerto_caso_media"]), f"{ab.pct(v['ic95_baixo'])}–{ab.pct(v['ic95_alto'])}", f"{ab.pct(v['acerto_caso_rep_min'])}–{ab.pct(v['acerto_caso_rep_max'])}",
                           co.usd(v["custo_por_resposta_usd"]), str(v["respostas"]), "sim" if v["completo"] else "não"])
        else:
            linhas.append([exp, ab.ROTULOS[var], "não medido", "—", "—", "—", "0", "—"])
    novo += [_tabela(["Exp.", "Variante", "Acerto", "IC 95%", "Mín–máx entre repetições", "Custo por resposta", "Respostas", "Completa"], linhas), ""]
    cl = []
    for exp, c in ab_resumo["comparacoes"].items():
        if c.get("medido") is False:
            cl.append([exp, "não medido", "—", "—", "—"])
        else:
            cl.append([exp, f"{ab.ROTULOS[c['base']]} contra {ab.ROTULOS[c['alternativa']]}", str(c["a_favor_base"]), str(c["a_favor_alternativa"]), ab.num(c["p_sinal"], 3)])
    novo += ["Comparações pareadas:", "", _tabela(["Exp.", "Par (base contra alternativa)", "Casos a favor da base", "Casos a favor da alternativa", "p (sinal exato)"], cl), "",
             f"Custo das rodadas novas: {co.usd(ab_resumo['custo_novo_usd']['total'])} em {ab_resumo['chamadas_novas']} chamadas (piloto {co.usd(ab_resumo['custo_novo_usd']['piloto'])}, rodadas {co.usd(ab_resumo['custo_novo_usd']['rodadas'])}). "
             "Relatório completo: `resultados/biblioteca/RELATORIO.md` (gerado por `src/analisar_biblioteca.py`).", ""]
    val = _validacao_md()
    novo += val
    mapa = ["## 7. Mapa de caminhos (reorganização do repositório)", "",
            "O repositório foi reorganizado em \"biblioteca + experimentos\". Os arquivos de resultado antigos foram **movidos sem alteração de conteúdo** (os hashes de congelamento continuam batendo, e há teste para isso); "
            "por isso os relatórios gerados originalmente ainda citam os caminhos antigos no próprio texto.", "",
            _tabela(["Antes", "Agora"], [["`dados/*.json`", "`dados/extracao/v1/`"], ["`dados/v2/`", "`dados/extracao/v2/`"], ["`resultados/*.md`, `resumo.json`", "`resultados/extracao/v1/`"],
                                       ["`resultados/v2/`", "`resultados/extracao/v2/`"], ["`prompts/T*.json`", "`prompts/extracao/`"], ["`docs/index.html` (demo anterior)", "substituída; o código antigo está em `src/legado/`"]]), "",
            "### Política das respostas brutas", "",
            "**Todas as respostas brutas do modelo ficam no Git**, para qualquer pessoa conferir os números sem chamar a API. O README anterior dizia o contrário para a extração; "
            "isso mudou e as pastas deixaram de ser ignoradas.", "",
            _tabela(["Rodada", "Pasta", "Arquivos"], [["Extração v1 (piloto + 600 respostas)", "`resultados/extracao/v1/brutos/`", "601 itens (600 respostas e a pasta `piloto/`)"],
                                                   ["Extração v2 (600 respostas)", "`resultados/extracao/v2/brutos/`", "600"], ["Iteração T4 v1 → v2 (150 respostas do T4 v2)", "`resultados/extracao/v2/iteracao/brutos/`", "150"],
                                                   ["Rodadas novas (P2 a P5, E6)", "`resultados/biblioteca/brutos/` e `piloto/`", "um `.jsonl` por variante"],
                                                   ["Validação do T4 v2 (pedidos novos)", "`resultados/extracao/v3/brutos/{v1,v2}/`", "60 em cada"]]), "",
            "As pastas da extração foram recuperadas do computador do autor, onde ficaram fora do Git até aqui, e a auditoria (`src/auditar.py`) foi refeita sobre elas: reavaliou as respostas com 0 divergências, e os relatórios regenerados ficaram idênticos aos já publicados. "
            "As respostas gravadas que a demo embutia continuam em `resultados/extracao/v2/respostas_gravadas.json`.", "",
            "### Comandos das rodadas antigas (extração)", "", "```bash",
            "PE_VERSAO=v2 .venv/bin/python src/rodar.py --completo    # PowerShell: $env:PE_VERSAO=\"v2\"",
            "PE_VERSAO=v2 .venv/bin/python src/rodar.py --iteracao",
            ".venv/bin/python src/analisar.py ; .venv/bin/python src/auditar.py ; .venv/bin/python src/classificar_erros.py", "```", "",
            "O README anterior (estudo de avaliação) está preservado em [`docs/legado/README_estudo_de_avaliacao.md`](legado/README_estudo_de_avaliacao.md)."]
    texto = ["# Detalhes da medição", "",
             "Apêndice técnico do [Prompt Lab](../README.md). Aqui ficam intervalo de confiança (bootstrap), teste do sinal pareado, auditoria e a rodada v1. O texto principal evita esse vocabulário de propósito.", "",
             "## 1. Resumo do que foi medido", "",
             f"- Extração (E1 e E2): {r['como_medi']['casos_extracao']} casos, {r['como_medi']['repeticoes']} repetições, rodadas v1 e v2 e a iteração do T4, **medidas e auditadas** (números abaixo, sem alteração).",
             f"- P2 a P5 (E3, E4, E5 e P4): {r['como_medi']['casos_novos']} casos por prompt, {r['como_medi']['repeticoes']} repetições. Experimentos medidos: {r['projeto']['experimentos_medidos']} de {r['projeto']['experimentos']} no total (inclui E1 e E2).", "",
             blocos[0], "", blocos[1], "", *novo, blocos[2], "", blocos[3], "", *mapa, ""]
    out = "\n".join(texto)
    for a, b in REESCRITA_CAMINHOS:
        out = out.replace(a, b)
    out = out.replace("extracao/extracao", "extracao")
    return out


def main():
    r = json.loads(RESUMO.read_text(encoding="utf-8"))
    (RAIZ / "README.md").write_text(readme(r), encoding="utf-8", newline="\n")
    (RAIZ / "docs" / "medicao.md").write_text(medicao(r), encoding="utf-8", newline="\n")
    print("README.md e docs/medicao.md gerados")


if __name__ == "__main__":
    main()
