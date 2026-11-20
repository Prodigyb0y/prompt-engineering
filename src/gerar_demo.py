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

TIPOS = {
    "completa": ("Mensagem completa", "Todas as informações estão no texto, escritas de forma direta. É o caso-base: se uma técnica errar aqui, algo está errado."),
    "campos_faltando": ("Informação faltando", "Algum dado não aparece no texto (por exemplo, fornecedor ou prazo). O correto é devolver null, sem inventar."),
    "unidades_variadas": ("Unidades diferentes", "A quantidade vem com unidades distintas e coladas ao número (25cx, 10 kg, 5 m). O modelo precisa separar número e unidade."),
    "valor_br": ("Valor no formato brasileiro", "Preços como R$ 15.800,00 ou R$ 2450,75: ponto de milhar e vírgula decimal. Errar isso muda o valor por um fator de mil."),
    "moeda_simbolo": ("Moeda por símbolo", "A moeda aparece só como símbolo (R$, US$, €). O modelo precisa traduzir para BRL, USD ou EUR."),
    "data_formato": ("Datas em formatos variados", "O prazo vem escrito de jeitos diferentes (14-jul-2026, 08/09/2026, 22 de outubro de 2026). Tudo deve virar AAAA-MM-DD."),
    "data_relativa": ("Prazo relativo (vira null)", "O prazo é \"daqui 15 dias\" ou parecido. Sem uma data de referência, não dá para calcular: o correto é null."),
    "fornecedor_apelido": ("Fornecedor por apelido", "O fornecedor é citado de forma curta (\"com a Ponto Certo\"). O modelo deve copiar o nome como aparece, sem completar."),
    "ruido": ("Ruído e erro de digitação", "Texto bagunçado: \"kkk\", \"presiso\", assinatura de celular. O modelo precisa ignorar o ruído e achar os dados."),
    "duas_quantidades": ("Duas quantidades no texto", "Há dois números (o pedido e, por exemplo, o estoque atual). O modelo precisa escolher a quantidade do item pedido."),
    "correcao": ("Autocorreção no texto", "A pessoa muda de ideia no meio do texto (\"Melhor ficar para 25/05/2026\"). Vale o último valor dito."),
    "valor_total": ("Só o valor total", "O texto traz o valor total, não o unitário. A regra do gabarito é dividir pela quantidade; os prompts não mencionam essa regra."),
    "numero_extenso": ("Número por extenso", "A quantidade vem em palavras (\"oito litros\"). O modelo precisa converter para número."),
    "moeda_extenso": ("Moeda por extenso", "O valor vem como \"89,90 dólares\" ou \"reais\"/\"euros\", sem símbolo. O modelo precisa mapear para USD, BRL ou EUR."),
    "email_longo": ("E-mail longo", "Os dados estão no meio de um e-mail com assunto paralelo e conversa de corredor. O modelo precisa achar a parte que importa."),
}

TECNICAS = {
    "T1": {"apelido": "Pedir direto", "analogia": "É como pedir a um estagiário: \"leia isso e me devolva estes campos\", sem mostrar nenhum modelo.",
           "como": "O prompt tem só a instrução e a lista de campos. Nenhum exemplo.",
           "quando": "Costuma bastar quando a tarefa é clara e o modelo é capaz. É o ponto de partida mais barato.",
           "limite": "Não diz como tratar casos esquisitos (dado ausente, valor só total). O modelo decide sozinho."},
    "T2": {"apelido": "Mostrar exemplos", "analogia": "É como entregar ao estagiário três pedidos já resolvidos e dizer: \"faça igual\".",
           "como": "O prompt inclui 3 exemplos completos (texto e JSON certo) antes do caso real.",
           "quando": "Ajuda quando o formato ou o estilo da resposta é difícil de descrever só com palavras.",
           "limite": "Gasta mais tokens (custo maior por chamada) e o modelo tende a imitar o que os exemplos mostram, inclusive o que eles não cobrem."},
    "T3": {"apelido": "Pensar em voz alta", "analogia": "É como pedir ao estagiário: \"escreva seu raciocínio num rascunho e só depois dê a resposta final\".",
           "como": "O modelo escreve o raciocínio dentro de <raciocinio> e o JSON final dentro de <json>. Só o <json> é lido.",
           "quando": "Costuma ajudar em tarefas com várias etapas ou contas, onde errar um passo estraga o resultado.",
           "limite": "A resposta fica bem mais longa: custa mais e demora mais. Em tarefas simples, pode não render ganho."},
    "T4": {"apelido": "Papel e regras", "analogia": "É como dar ao estagiário a descrição do cargo e o manual da casa antes de começar a trabalhar.",
           "como": "O papel, as regras e o formato ficam no system prompt, a parte da instrução que o modelo trata como orientação permanente.",
           "quando": "Bom para padronizar o comportamento: as mesmas regras valem para todo caso, e ficam num só lugar para revisar.",
           "limite": "O resultado depende das regras escritas. Regra que falta ou que foi mal escrita vira erro previsível."},
}

TEMPLATE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laboratório de prompt engineering</title>
<style>
:root{--tx:#1c2433;--mut:#5b6678;--bg:#f5f7fb;--card:#fff;--bd:#d9dfea;--ac:#4a3fd6;--ok:#1f7a3d;--er:#b3261e;--av:#fff6df}
*{box-sizing:border-box}
body{font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;color:var(--tx);background:var(--bg)}
main{max-width:1000px;margin:0 auto;padding:0 1rem 3rem}
header{background:linear-gradient(135deg,#2a2370,#4a3fd6);color:#fff;padding:2rem 1rem 2.2rem}
header .in{max-width:1000px;margin:0 auto}
header h1{margin:.2rem 0 .5rem;font-size:1.8rem;line-height:1.2}
header p{margin:.3rem 0;max-width:46rem;opacity:.95}
header a{color:#fff;text-decoration:underline}
.chips{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.8rem}
.chip{background:rgba(255,255,255,.18);border-radius:99px;padding:.15rem .7rem;font-size:.85rem}
h2{font-size:1.3rem;margin:2.4rem 0 .3rem}
h2+.sub{color:var(--mut);margin:0 0 1rem}
h3{font-size:1rem;margin:1rem 0 .3rem}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:1rem 1.1rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:.9rem}
.big{font-size:1.05rem}
.aviso{background:var(--av);border:1px solid #e3c875;border-radius:10px;padding:.8rem 1rem}
.tec h3{margin:.1rem 0 .1rem;font-size:1.1rem}
.tec .ap{color:var(--ac);font-weight:600;font-size:.9rem}
.tec p{margin:.4rem 0}
.tec .met{background:#eef0fb;border-radius:8px;padding:.45rem .6rem;font-size:.88rem;margin-top:.6rem}
.rot{font-weight:600;font-size:.82rem;color:var(--mut);text-transform:uppercase;letter-spacing:.03em;display:block;margin-top:.55rem}
details{margin-top:.6rem}summary{cursor:pointer;color:var(--ac);font-weight:600;font-size:.9rem}
pre{white-space:pre-wrap;word-break:break-word;background:#f1f3f8;padding:.6rem;border-radius:8px;font-size:.8rem;margin:.4rem 0;line-height:1.45}
table{border-collapse:collapse;width:100%;font-size:.88rem;background:var(--card)}
th,td{border:1px solid var(--bd);padding:.4rem .55rem;text-align:left}th{background:#eceff6}
.num{text-align:right;font-variant-numeric:tabular-nums}
.ctl{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.8rem;margin-bottom:.8rem}
.ctl label{font-weight:600;font-size:.88rem;display:block}
select{width:100%;font-size:1rem;padding:.5rem;border:1px solid var(--bd);border-radius:8px;background:#fff;margin-top:.2rem;color:var(--tx)}
.desc{background:#eef0fb;border-left:4px solid var(--ac);border-radius:6px;padding:.6rem .8rem;margin:.4rem 0 1rem}
.out{border:2px solid var(--bd);border-radius:10px;padding:.6rem;background:#fff}.out.ok{border-color:var(--ok)}.out.erro{border-color:var(--er)}
.tag{font-weight:700;font-size:.85rem}.tag.ok{color:var(--ok)}.tag.erro{color:var(--er)}
.legenda{color:var(--mut);font-size:.88rem}
.nota{color:var(--mut);font-size:.88rem}
@media(max-width:560px){header h1{font-size:1.5rem}}
</style></head><body>
<header><div class="in">
<h1>Laboratório de prompt engineering</h1>
<p><strong>Mesma tarefa, mesmos casos, quatro técnicas de prompt: o que acerta mais, e quanto custa cada acerto.</strong></p>
<p>Esta página mostra, com números medidos, como a forma de pedir muda o resultado de uma IA numa tarefa de trabalho. Não precisa saber programar para acompanhar.</p>
<div class="chips"><span class="chip">Modelo: claude-haiku-5-5</span><span class="chip">50 casos · 4 técnicas · 3 repetições</span><span class="chip">Dados 100% fictícios (conjunto __VERSAO__)</span></div>
<p style="margin-top:.8rem"><a href="__OUTRA__">__OUTRA_TXT__</a></p>
</div></header>
<main>

<h2>1. O que é um prompt?</h2>
<p class="sub">Em uma frase: prompt é a instrução que você escreve para a IA.</p>
<div class="card big">
<p>Pense na IA como um profissional muito rápido que não conhece o seu contexto. O que ele entrega depende de como você pede: o que ele deve fazer, em que formato, com quais regras e se há exemplos de um bom resultado. Esse texto de pedido é o <strong>prompt</strong>.</p>
<p>A tarefa deste laboratório é típica de qualquer área: alguém escreve um pedido de compra em texto livre (como num e-mail) e o sistema precisa transformar isso em dados organizados (item, quantidade, valor, prazo, fornecedor). Um advogado faria o mesmo com cláusulas de contratos, e um time de RH, com currículos.</p>
<pre>Entrada (texto livre):  "Oi, preciso de 25cx de etiqueta adesiva para Compras. R$ 2450,75 cada, com a Distribuidora Pinheiro, até 17-ago-2026."

Saída esperada (dados organizados):  item, quantidade 25, unidade cx, valor 2450.75, moeda BRL, fornecedor, prazo 2026-08-17</pre>
</div>

<h2>2. Por que engenharia de prompt?</h2>
<p class="sub">Engenharia de prompt é escolher e testar a forma de pedir, em vez de confiar na primeira tentativa.</p>
<div class="grid">
<div class="card"><strong>Resposta no formato certo</strong><p>Sem instrução, a IA responde em texto solto. Com o formato definido, ela devolve dados que um sistema consegue ler sem retrabalho humano.</p></div>
<div class="card"><strong>Menos erro nos casos difíceis</strong><p>Regras claras dizem o que fazer quando falta dado, quando o valor vem em outro formato ou quando o texto é confuso.</p></div>
<div class="card"><strong>Custo e velocidade sob controle</strong><p>Cada técnica gasta uma quantidade diferente de texto (tokens) e demora um tempo diferente. Dá para escolher a que compensa.</p></div>
<div class="card"><strong>Resultado que se pode auditar</strong><p>Com o prompt versionado e um gabarito fixo, qualquer pessoa confere se a mudança melhorou de verdade ou só pareceu melhorar.</p></div>
</div>
<div class="aviso" style="margin-top:1rem"><strong>O que este teste mostrou:</strong> <span id="aviso"></span></div>
<p class="nota">Os quatro pontos acima são os motivos para medir. Este teste usa um modelo e 50 casos, então não prova que as técnicas se comportam assim em outras tarefas.</p>

<h2>3. As quatro técnicas comparadas</h2>
<p class="sub">Todas recebem os mesmos 50 textos e devolvem o mesmo JSON. Só muda a forma de pedir.</p>
<div class="grid" id="tecnicas"></div>

<h2>4. Resultado por técnica</h2>
<p class="sub">Cada linha é uma técnica, medida nos mesmos casos (resultado oficial).</p>
<div style="overflow-x:auto"><table id="tabela"></table></div>
<p class="legenda">Como ler: <strong>acerto por caso</strong> conta um caso como certo só se os 8 campos estiverem certos. <strong>IC 95%</strong> é a faixa em que o acerto verdadeiro provavelmente está; se as faixas de duas técnicas se sobrepõem, não dá para dizer que uma é melhor. <strong>Custo por acerto</strong> é o gasto total dividido pelos casos certos.</p>
<p class="nota" id="notas"></p>

<h2>5. Explorador de casos</h2>
<p class="sub">Escolha um tipo de caso, depois um exemplo, e veja o texto original, a resposta certa e o que cada técnica devolveu.</p>
<div class="ctl">
<div><label for="tipo">1. Tipo de caso</label><select id="tipo"></select></div>
<div><label for="caso">2. Exemplo</label><select id="caso"></select></div>
<div><label for="rep">3. Repetição</label><select id="rep"></select></div>
</div>
<div class="desc"><strong>O que este tipo testa:</strong> <span id="desctipo"></span></div>
<div id="detalhe"></div>
<p class="nota">Repetição: cada caso foi rodado 3 vezes por técnica, porque o modelo pode variar de uma vez para outra.</p>
</main>
<script id="dados" type="application/json">__DADOS__</script>
<script>
const D = JSON.parse(document.getElementById('dados').textContent);
const pct = x => (100*x).toFixed(1).replace('.',',')+'%';
const usd = x => x.toFixed(6).replace('.',',');
const el = (t, txt, cls) => { const e=document.createElement(t); if(txt!==undefined) e.textContent=txt; if(cls) e.className=cls; return e; };
document.getElementById('aviso').textContent = D.aviso;
document.getElementById('notas').textContent = D.notas;

// cartões das técnicas
const tec = document.getElementById('tecnicas');
D.resumo.forEach(r=>{
  const i = D.tecnicas[r.id]; const c = el('div',undefined,'card tec');
  c.appendChild(el('span',r.id+' · '+r.tecnica,'ap'));
  c.appendChild(el('h3',i.apelido));
  c.appendChild(el('p',i.analogia));
  c.appendChild(el('span','Como funciona aqui','rot')); c.appendChild(el('p',i.como));
  c.appendChild(el('span','Quando costuma ajudar','rot')); c.appendChild(el('p',i.quando));
  c.appendChild(el('span','Limite','rot')); c.appendChild(el('p',i.limite));
  c.appendChild(el('div','Neste teste: acerto '+pct(r.acerto)+' · custo por caso US$ '+usd(r.custo_caso)+' · latência média '+r.lat.toFixed(2).replace('.',',')+' s','met'));
  const d = el('details'); d.appendChild(el('summary','Ver o prompt real ('+r.versao+', hash '+r.hash+')'));
  const p = D.prompts[r.id];
  if(p.system){ d.appendChild(el('span','System prompt','rot')); d.appendChild(el('pre',p.system)); }
  d.appendChild(el('span','Mensagem enviada (o texto do caso entra no lugar de {texto})','rot')); d.appendChild(el('pre',p.user));
  c.appendChild(d); tec.appendChild(c);
});

// tabela
const tb = document.getElementById('tabela');
const cab = ['Técnica','Prompt','Acerto por caso','IC 95%','Mín–máx entre repetições','Custo por caso (US$)','Custo por acerto (US$)','Latência média (s)'];
const h = el('tr'); cab.forEach(c=>h.appendChild(el('th',c))); tb.appendChild(h);
D.resumo.forEach(r=>{ const tr=el('tr');
  [r.id+' '+r.tecnica, r.versao+' '+r.hash, pct(r.acerto), pct(r.ic_lo)+'–'+pct(r.ic_hi), pct(r.rep_min)+'–'+pct(r.rep_max), usd(r.custo_caso), usd(r.custo_acerto), r.lat.toFixed(2).replace('.',',')]
   .forEach((v,i)=>tr.appendChild(el('td',v,i>=2?'num':''))); tb.appendChild(tr); });

// explorador
const st=document.getElementById('tipo'), sc=document.getElementById('caso'), sr=document.getElementById('rep');
const tipos=[]; D.casos.forEach((c,i)=>{ let t=tipos.find(x=>x.tipo===c.tipo); if(!t){ t={tipo:c.tipo,idx:[]}; tipos.push(t);} t.idx.push(i); });
tipos.forEach((t,k)=>{ const m=D.tipos[t.tipo]||[t.tipo,'']; const o=el('option',m[0]+' ('+t.idx.length+' '+(t.idx.length>1?'casos':'caso')+')'); o.value=k; st.appendChild(o); });
for(let i=1;i<=D.repeticoes;i++){ const o=el('option','Repetição '+i); o.value=i; sr.appendChild(o); }
const rotulo = c => { const g=c.gabarito; const q=String(g.quantidade).replace('.',','); return q+' '+g.unidade+' de '+g.item; };
function trocarTipo(){
  const t=tipos[st.value]; sc.replaceChildren();
  t.idx.forEach((i,n)=>{ const c=D.casos[i]; const o=el('option',c.id+' · pedido de '+rotulo(c)); o.value=i; sc.appendChild(o); });
  document.getElementById('desctipo').textContent=(D.tipos[t.tipo]||['',''])[1];
  mostrar();
}
function mostrar(){
  const c=D.casos[sc.value], rep=+sr.value, box=document.getElementById('detalhe'); box.replaceChildren();
  box.appendChild(el('h3','Texto da solicitação (o que a pessoa escreveu)')); box.appendChild(el('pre',c.texto));
  box.appendChild(el('h3','Gabarito (a resposta certa, escrita antes de rodar)')); box.appendChild(el('pre',JSON.stringify(c.gabarito,null,2)));
  box.appendChild(el('h3','O que cada técnica respondeu (repetição '+rep+')'));
  const g=el('div',undefined,'grid');
  Object.keys(c.saidas).sort().forEach(t=>{ const s=c.saidas[t][rep-1]; if(!s) return;
    const card=el('div',undefined,'out '+(s.correto?'ok':'erro'));
    card.appendChild(el('strong',t+' '+D.tecnicas[t].apelido+' '));
    card.appendChild(el('span',s.correto?'✓ correto':'✗ errado (oficial)','tag '+(s.correto?'ok':'erro')));
    if(s.classe && s.classe!=='correto') card.appendChild(el('div','Classe do erro: '+s.classe,'nota'));
    card.appendChild(el('pre',s.resposta)); g.appendChild(card); });
  box.appendChild(g);
}
st.onchange=trocarTipo; sc.onchange=mostrar; sr.onchange=mostrar; trocarTipo();
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
    prompts = {}
    for t in resumo:
        arq = next((RAIZ / "prompts").glob(f"{t}_*_{resumo[t]['prompt_versao']}.json"))
        pj = json.loads(arq.read_text(encoding="utf-8"))
        prompts[t] = {"system": pj.get("system", ""), "user": pj["user_template"]}
    return {"tipos": {k: list(v) for k, v in TIPOS.items()}, "tecnicas": {k: TECNICAS[k] for k in resumo},
            "prompts": prompts, "resumo": tabela, "nomes": nomes, "casos": ordenados, "repeticoes": max(r["repeticoes"] for r in resumo.values()),
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
