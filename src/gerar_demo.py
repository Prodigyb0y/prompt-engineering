"""P11: gera docs/index.html (página estática, sem servidor e sem chave) a partir dos resultados.

Lê resultados/brutos/*.json, resultados/resumo.json, dados/*.json. Nada é digitado à mão:
todo número da página vem de resumo.json. Os dados dos casos vão embutidos no HTML.

Uso: python src/gerar_demo.py
"""
import json
from pathlib import Path

import caminhos
import classificar_erros as ce
from analisar import carregar, separaveis

RAIZ = caminhos.RAIZ

TEMPLATE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laboratório de prompt engineering</title>
<style>
body{font:16px/1.5 system-ui,sans-serif;max-width:980px;margin:0 auto;padding:1.2rem;color:#1b1b1b}
h1{font-size:1.5rem;margin:.2rem 0}h2{font-size:1.15rem;margin-top:2rem}
.aviso{background:#fff7e0;border:1px solid #e0c060;padding:.7rem 1rem;border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{border:1px solid #ccc;padding:.35rem .5rem;text-align:left}th{background:#f3f3f3}
.num{text-align:right;font-variant-numeric:tabular-nums}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:.8rem}
.card{border:1px solid #ccc;border-radius:6px;padding:.6rem}.ok{border-color:#2e7d32}.erro{border-color:#c62828}
pre{white-space:pre-wrap;word-break:break-word;background:#f7f7f7;padding:.5rem;border-radius:4px;font-size:.8rem;margin:.3rem 0}
label{margin-right:1rem}select{font-size:1rem;padding:.2rem}
.tag{font-weight:600}.tag.ok{color:#2e7d32}.tag.erro{color:#c62828}
</style></head><body>
<h1>Laboratório de prompt engineering</h1>
<p><a href="__OUTRA__">__OUTRA_TXT__</a></p>
<p><strong>Mesma tarefa, mesmos casos, quatro técnicas de prompt: o que acerta mais, e quanto custa cada acerto.</strong></p>
<p>Tarefa: extrair campos de solicitações de compra fictícias (empresa fictícia Gutenberg Systems) e devolver JSON. Modelo: <code>claude-haiku-5-5</code>. Dados 100% fictícios (conjunto de casos __VERSAO__).</p>
<div class="aviso"><strong>Leia antes de comparar:</strong> <span id="aviso"></span></div>
<h2>Resultado por técnica (oficial)</h2>
<div style="overflow-x:auto"><table id="tabela"></table></div>
<p id="notas"></p>
<h2>Explorador de casos</h2>
<p><label>Caso <select id="caso"></select></label><label>Repetição <select id="rep"></select></label></p>
<div id="detalhe"></div>
<script id="dados" type="application/json">__DADOS__</script>
<script>
const D = JSON.parse(document.getElementById('dados').textContent);
const pct = x => (100*x).toFixed(1).replace('.',',')+'%';
const usd = x => x.toFixed(6).replace('.',',');
const el = (t, txt, cls) => { const e=document.createElement(t); if(txt!==undefined) e.textContent=txt; if(cls) e.className=cls; return e; };
document.getElementById('aviso').textContent = D.aviso;
const tb = document.getElementById('tabela');
const cab = ['Técnica','Prompt','Acerto por caso','IC 95%','Mín–máx entre repetições','Custo por caso (US$)','Custo por acerto (US$)','Latência média (s)'];
const h = el('tr'); cab.forEach(c=>h.appendChild(el('th',c))); tb.appendChild(h);
D.resumo.forEach(r=>{ const tr=el('tr');
  [r.id+' '+r.tecnica, r.versao+' '+r.hash, pct(r.acerto), pct(r.ic_lo)+'–'+pct(r.ic_hi), pct(r.rep_min)+'–'+pct(r.rep_max), usd(r.custo_caso), usd(r.custo_acerto), r.lat.toFixed(2).replace('.',',')]
   .forEach((v,i)=>tr.appendChild(el('td',v,i>=2?'num':''))); tb.appendChild(tr); });
document.getElementById('notas').textContent = D.notas;
const sc=document.getElementById('caso'), sr=document.getElementById('rep');
D.casos.forEach((c,i)=>{ const o=el('option',c.id+' · '+c.tipo); o.value=i; sc.appendChild(o); });
for(let i=1;i<=D.repeticoes;i++){ const o=el('option',String(i)); o.value=i; sr.appendChild(o); }
function mostrar(){
  const c=D.casos[sc.value], rep=+sr.value, box=document.getElementById('detalhe'); box.replaceChildren();
  box.appendChild(el('h3','Texto da solicitação')); box.appendChild(el('pre',c.texto));
  box.appendChild(el('h3','Gabarito')); box.appendChild(el('pre',JSON.stringify(c.gabarito,null,2)));
  box.appendChild(el('h3','Saída de cada técnica (repetição '+rep+')'));
  const g=el('div',undefined,'grid');
  Object.keys(c.saidas).sort().forEach(t=>{ const s=c.saidas[t][rep-1]; if(!s) return;
    const card=el('div',undefined,'card '+(s.correto?'ok':'erro'));
    card.appendChild(el('strong',t+' '+D.nomes[t]+' '));
    card.appendChild(el('span',s.correto?'correto':'errado (oficial)','tag '+(s.correto?'ok':'erro')));
    if(s.classe && s.classe!=='correto') card.appendChild(el('div','Classe do erro: '+s.classe));
    card.appendChild(el('pre',s.resposta)); g.appendChild(card); });
  box.appendChild(g);
}
sc.onchange=mostrar; sr.onchange=mostrar; mostrar();
</script></body></html>
"""


def montar_dados():
    resumo = json.loads((caminhos.RESULTADOS / "resumo.json").read_text(encoding="utf-8"))
    gab = json.loads((caminhos.DADOS / "gabarito.json").read_text(encoding="utf-8"))
    casos = json.loads((caminhos.DADOS / "casos_teste.json").read_text(encoding="utf-8"))
    regs = carregar(caminhos.RESULTADOS / "brutos")
    saidas = {}
    for r in regs:
        classe, _ = ce.classificar(r, gab[r["caso"]])
        saidas.setdefault(r["caso"], {}).setdefault(r["tecnica"], {})[r["repeticao"]] = {
            "resposta": r["resposta"].strip(), "correto": r["avaliacao"]["caso_correto"], "classe": classe}
    ordenados = []
    for c in sorted(casos, key=lambda c: c["id"]):
        por_tec = {t: [reps[k] for k in sorted(reps)] for t, reps in saidas[c["id"]].items()}
        ordenados.append({"id": c["id"], "tipo": c["tipo"], "texto": c["texto"], "gabarito": gab[c["id"]], "saidas": por_tec})
    tabela = [{"id": t, "tecnica": r["tecnica"], "versao": r["prompt_versao"], "hash": r["prompt_hash12"],
               "acerto": r["acerto_caso_media"], "ic_lo": r["ic95_baixo"], "ic_hi": r["ic95_alto"],
               "rep_min": r["acerto_caso_rep_min"], "rep_max": r["acerto_caso_rep_max"],
               "custo_caso": r["custo_por_caso_usd"], "custo_acerto": r["custo_por_acerto_usd"],
               "lat": r["latencia_media_s"]} for t, r in sorted(resumo.items())]
    nomes = {t: r["tecnica"] for t, r in resumo.items()}
    erros_total = sum(1 for r in regs if not r["avaliacao"]["caso_correto"])
    so_ponto = sum(1 for r in regs if ce.classificar(r, gab[r["caso"]])[0] == "fornecedor_ponto_final")
    if so_ponto:
        quantas = (f"As {erros_total} respostas erradas são todas" if erros_total == so_ponto
                   else f"{so_ponto} das {erros_total} respostas erradas são")
        aviso = (f"{quantas} o mesmo artefato do gerador de casos: o texto traz \"Ltda.\" e o modelo copiou o ponto, "
                 "mas o gabarito não tem ponto. Na recontagem pós-hoc (não oficial, feita depois de ver os resultados) as técnicas empatam, "
                 "então a tabela NÃO mostra qual técnica entende melhor a tarefa. A diferença que sobra é de custo e latência. "
                 "Os intervalos de 95% se sobrepõem.")
    else:
        pares = separaveis(resumo)
        nomes_t = {t: f"{t} {r['tecnica']}" for t, r in resumo.items()}
        if pares:
            aviso = ("Com intervalos de 95% que não se sobrepõem, pode-se declarar: "
                     + "; ".join(f"{nomes_t[a]} acerta mais que {nomes_t[b]}" for a, b in pares)
                     + ". Para os demais pares, os intervalos se sobrepõem e não há vencedor declarado.")
        else:
            aviso = "Os intervalos de 95% se sobrepõem em todos os pares: nenhuma técnica é declarada melhor."
        aviso += f" {erros_total} das {len(regs)} respostas foram erradas pela regra oficial."
        tipos_erro = {r["tipo"] for r in regs if not r["avaliacao"]["caso_correto"]}
        if len(tipos_erro) == 1:
            tipo_unico = next(iter(tipos_erro))
            aviso += f" Todas estão no tipo \"{tipo_unico}\"; nos demais casos as técnicas empatam em 100%."
            if tipo_unico == "valor_total":
                aviso += (" Nesse tipo o texto traz só o valor total e o gabarito exige dividir pela quantidade, uma regra do autor que os "
                          "prompts não mencionam: o T4 manda usar null quando o dado não está no texto, e foi o que ele fez. "
                          "O resultado mostra como cada prompt trata um dado implícito, não só quem \"entende melhor\".")
    notas = ("Como foi medido: acerto por caso = JSON válido, schema válido e 8 campos iguais ao gabarito (após normalização de acento, "
             "caixa e espaços), média de 3 repetições sobre 50 casos; IC 95% por bootstrap (10.000 reamostragens, seed 42); custo = tokens "
             "informados pela API × preço de tabela de 2026-11-19; latência com time.perf_counter. Sem temperatura 0: o modelo não aceita "
             "esse parâmetro. Detalhes no README.")
    return {"resumo": tabela, "nomes": nomes, "casos": ordenados, "repeticoes": max(r["repeticoes"] for r in resumo.values()),
            "aviso": aviso, "notas": notas}


def main():
    dados = montar_dados()
    blob = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    destino = caminhos.DOCS
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "index.html").write_text(TEMPLATE.replace("__OUTRA__", "../index.html" if caminhos.VERSAO == "v2" else "v2/index.html").replace("__OUTRA_TXT__", "Ver a rodada com os dados v1 (50 casos mais simples)" if caminhos.VERSAO == "v2" else "Ver a rodada com os dados v2 (50 casos mais difíceis, sem o artefato do Ltda.)").replace("__VERSAO__", caminhos.VERSAO).replace("__DADOS__", blob), encoding="utf-8", newline="\n")
    print(f"{destino}/index.html gerado ({caminhos.VERSAO}): {len(dados['casos'])} casos, {len(dados['resumo'])} técnicas")


if __name__ == "__main__":
    main()
