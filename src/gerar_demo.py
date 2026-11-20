"""P11: gera docs/index.html (página estática, sem servidor e sem chave) a partir dos resultados.

Lê resultados/brutos/*.json, resultados/resumo.json, dados/*.json. Nada é digitado à mão:
todo número da página vem de resumo.json. Os dados dos casos vão embutidos no HTML.

Uso: python src/gerar_demo.py
"""
import json
from pathlib import Path

import caminhos
import prompts_lib
from conteudo_demo import ANATOMIA, ANATOMIA_NOTA, LIMITACOES, METRICAS, PRIORIDADES, QA
import classificar_erros as ce
from analisar import carregar, comparacoes, separaveis
from validador import parse as vparse

RAIZ = caminhos.RAIZ
CAMPOS = ["solicitante_area", "item", "quantidade", "unidade", "prazo_entrega", "valor_unitario", "moeda", "fornecedor"]

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

COMPARA = [
    ("Exemplos no prompt", {"T1": "Nenhum", "T2": "3 exemplos resolvidos", "T3": "Nenhum", "T4": "Nenhum"}),
    ("Raciocínio antes da resposta", {"T1": "Não pedido", "T2": "Não pedido", "T3": "Pedido, em <raciocinio>", "T4": "Não pedido"}),
    ("Onde ficam as regras", {"T1": "Só a instrução e os campos", "T2": "Instrução, campos e exemplos", "T3": "Instrução e campos", "T4": "System prompt com papel e regras"}),
]

TEMPLATE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laboratório de prompt engineering · avaliação de técnicas de prompt</title>
<style>
:root{--tx:#18212f;--mut:#56627a;--bg:#fff;--soft:#f4f6f9;--bd:#d5dbe5;--ac:#0b4f8a;--ok:#1b6e3a;--okl:#e5f3ea;--er:#a3231a;--erl:#fbebe9;--av:#fff7e1}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{font:15.5px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:0;color:var(--tx);background:var(--bg)}
.w{max-width:960px;margin:0 auto;padding:0 1.1rem}
header{border-bottom:1px solid var(--bd);padding:1.8rem 0 1.2rem;background:var(--soft)}
header h1{margin:0 0 .3rem;font-size:1.65rem;line-height:1.25;letter-spacing:-.01em}
header .sub{margin:0;color:var(--mut);max-width:44rem}
.meta{margin:.9rem 0 0;color:var(--mut);font-size:.84rem}
.seg{display:inline-block;border:1px solid var(--bd);padding:.2rem .8rem;font-size:.84rem;text-decoration:none;color:var(--ac);background:#fff}
.seg:first-child{border-radius:6px 0 0 6px}.seg+.seg{border-radius:0 6px 6px 0;margin-left:-1px}
.seg.on{background:var(--ac);border-color:var(--ac);color:#fff;font-weight:600}
.rod{margin:.9rem 0 0;display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;font-size:.86rem;color:var(--mut)}
nav{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid var(--bd)}
nav .w{display:flex;overflow-x:auto;gap:.2rem}
nav a{flex:0 0 auto;padding:.7rem .8rem;font-size:.86rem;color:var(--mut);text-decoration:none;border-bottom:2px solid transparent;white-space:nowrap}
nav a:hover{color:var(--ac)}nav a.on{color:var(--ac);border-bottom-color:var(--ac);font-weight:600}
section{padding:1.6rem 0 .4rem;scroll-margin-top:3rem}
h2{font-size:1.2rem;margin:0 0 .2rem;letter-spacing:-.005em}
h2 .n{color:var(--mut);font-weight:400;margin-right:.35rem}
h3{font-size:.95rem;margin:1.3rem 0 .3rem}
p.lead{color:var(--mut);margin:.1rem 0 .9rem;max-width:46rem}
.ficha{display:grid;grid-template-columns:130px 1fr;gap:.55rem 1.1rem;margin:0;padding:1rem 1.1rem;border:1px solid var(--bd);border-radius:6px;background:var(--soft)}
.ficha dt{font-weight:700;color:var(--mut);font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;padding-top:.2rem}
.ficha dd{margin:0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:.7rem;margin:1rem 0 0}
.tile{border:1px solid var(--bd);border-radius:6px;padding:.7rem .9rem}
.tile .k{font-size:.74rem;font-weight:700;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.tile .v{font-size:1.3rem;font-weight:700;line-height:1.3;margin:.1rem 0}
.tile .d{font-size:.82rem;color:var(--mut)}
table{border-collapse:collapse;width:100%;font-size:.86rem}
th,td{border:1px solid var(--bd);padding:.4rem .55rem;text-align:left;vertical-align:top}th{background:var(--soft);font-weight:600}
.num{text-align:right;font-variant-numeric:tabular-nums}
.tw{overflow-x:auto}
.cap{font-size:.82rem;color:var(--mut);margin:.4rem 0 0}
.nota{border-left:3px solid #e0b64a;background:var(--av);padding:.6rem .9rem;margin:.9rem 0;font-size:.9rem}
details{margin:.5rem 0}summary{cursor:pointer;color:var(--ac);font-weight:600;font-size:.88rem}
pre{white-space:pre-wrap;word-break:break-word;background:var(--soft);border:1px solid var(--bd);padding:.6rem;border-radius:4px;font:12.5px/1.45 ui-monospace,Menlo,Consolas,monospace;margin:.35rem 0}
.rot{font-weight:700;font-size:.74rem;color:var(--mut);text-transform:uppercase;letter-spacing:.04em;display:block;margin-top:.6rem}
.barra{display:grid;grid-template-columns:minmax(120px,190px) 1fr 5.6rem;gap:.6rem;align-items:center;margin:.3rem 0;font-size:.88rem}
.trilho{position:relative;height:20px;background:#e9edf3}
.pre{position:absolute;left:0;top:0;bottom:0;background:var(--ac);opacity:.88}
.ic{position:absolute;top:50%;height:2px;background:#111;transform:translateY(-50%)}
.ic::before,.ic::after{content:"";position:absolute;top:-5px;width:2px;height:12px;background:#111}.ic::before{left:0}.ic::after{right:0}
.barra .v{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
.mapa td.c{text-align:center;font-variant-numeric:tabular-nums;cursor:pointer;font-weight:600}
.mapa small{display:block;font-weight:400;font-size:.72rem;opacity:.8}
.mapa .h100{background:var(--okl);color:var(--ok)}.mapa .h90{background:#f1f6d8}.mapa .h70{background:var(--av)}.mapa .h0{background:var(--erl);color:var(--er)}
.ctl{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.8rem;margin:.5rem 0 .8rem}
.ctl label{font-weight:600;font-size:.8rem;display:block;color:var(--mut)}
select{width:100%;font-size:.95rem;padding:.45rem;border:1px solid var(--bd);border-radius:4px;background:#fff;margin-top:.2rem;color:var(--tx)}
.desc{border-left:3px solid var(--ac);background:var(--soft);padding:.5rem .8rem;margin:.3rem 0 .8rem;font-size:.9rem}
.cmp td.ok{background:var(--okl)}.cmp td.erro{background:var(--erl);color:var(--er);font-weight:600}
.cmp td,.cmp th{font-size:.8rem;font-family:ui-monospace,Menlo,Consolas,monospace}.cmp th{font-family:inherit}
.por{border-left:3px solid var(--er);background:var(--erl);padding:.45rem .8rem;margin:.45rem 0;font-size:.88rem}
.por b{display:block}
ul.lim{margin:.3rem 0 0;padding-left:1.2rem}ul.lim li{margin:.3rem 0}
footer{margin-top:2.2rem;border-top:1px solid var(--bd);background:var(--soft);padding:1rem 0 1.6rem;font-size:.84rem;color:var(--mut)}
footer a,.lk{color:var(--ac)}
@media(max-width:560px){.ficha{grid-template-columns:1fr;gap:.1rem}.ficha dd{margin-bottom:.55rem}header h1{font-size:1.4rem}.barra{grid-template-columns:100px 1fr 4.6rem}}
</style></head><body>
<header><div class="w">
<h1>Laboratório de prompt engineering</h1>
<p class="sub">Avaliação comparativa de quatro técnicas de prompt na extração estruturada de pedidos de compra em texto livre.</p>
<p class="meta">Modelo claude-haiku-5-5 · 50 casos × 4 técnicas × 3 repetições · dados sintéticos de empresa fictícia (Gutenberg Systems)</p>
<div class="rod"><span>__LINKS__</span><span>__DESCRODADA__</span></div>
</div></header>
<nav><div class="w" id="nav">
<a href="#resumo">Resumo</a><a href="#metodologia">Metodologia</a><a href="#resultados">Resultados</a><a href="#erros">Análise de erros</a><a href="#iteracao">Iteração de prompt</a><a href="#explorador">Explorador de casos</a><a href="#limitacoes">Limitações</a>
</div></nav>
<div class="w">

<section id="resumo">
<h2><span class="n">1.</span>Resumo executivo</h2>
<p class="lead">Equipes de negócio recebem solicitações em texto livre que precisam virar dados estruturados. A forma de pedir ao modelo (o prompt) afeta o acerto, o custo e o tempo de resposta. Este estudo mede essas três coisas na mesma tarefa.</p>
<dl class="ficha" id="ficha"></dl>
<div class="tiles" id="tiles"></div>
</section>

<section id="metodologia">
<h2><span class="n">2.</span>Metodologia</h2>
<h3>Tarefa e dados</h3>
<p>Dado um pedido de compra escrito como num e-mail, o modelo devolve um JSON com 8 campos: <code>solicitante_area</code>, <code>item</code>, <code>quantidade</code>, <code>unidade</code> (un, kg, m, l ou cx), <code>prazo_entrega</code> (AAAA-MM-DD ou null), <code>valor_unitario</code>, <code>moeda</code> (BRL, USD, EUR ou null) e <code>fornecedor</code>. Os 50 textos são sintéticos, gerados por script (seed 42), cada um com o gabarito escrito e congelado (hash registrado) antes da primeira execução. Cada caso pertence a um tipo (por exemplo, valor em formato brasileiro, prazo relativo, informação ausente).</p>
<h3>Técnicas avaliadas</h3>
<div class="tw"><table id="t-tec"></table></div>
<p class="cap">Os quatro prompts são idênticos para todos os casos e estão versionados no repositório (versão e hash SHA-256 truncado em 12 caracteres). O texto completo de cada um está abaixo.</p>
<div id="prompts"></div>
<h3>Anatomia de um prompt estruturado (T4, system prompt)</h3>
<div class="tw"><table id="anat"></table></div>
<p class="cap" id="anat-nota"></p>
<h3>Métricas e como foram medidas</h3>
<div class="tw"><table id="t-met"></table></div>
</section>

<section id="resultados">
<h2><span class="n">3.</span>Resultados</h2>
<p class="lead">Resultado oficial da rodada selecionada. Todas as técnicas receberam os mesmos casos.</p>
<div class="nota" id="aviso"></div>
<h3>Acerto por caso</h3>
<p class="cap" style="margin-top:0">Maior é melhor. A barra preta é o intervalo de confiança de 95%. Uma técnica só é declarada melhor que outra se os intervalos não se sobrepõem e o teste do sinal exato pareado dá p &lt; 0,05 (tabela abaixo).</p>
<div id="g-acerto"></div>
<h3>Comparações pareadas entre técnicas</h3>
<div class="tw"><table id="pares"></table></div>
<p class="cap">Teste do sinal exato, bilateral, por caso (cada caso conta uma vez, com o acerto médio das repetições; empates saem do teste). Com poucos casos discordantes, mesmo 4 a 0 não chega a p &lt; 0,05.</p>
<h3>Custo por caso (US$)</h3>
<p class="cap" style="margin-top:0">Menor é melhor.</p>
<div id="g-custo"></div>
<h3>Latência média por chamada (s)</h3>
<p class="cap" style="margin-top:0">Menor é melhor.</p>
<div id="g-lat"></div>
<h3>Tabela completa</h3>
<div class="tw"><table id="tabela"></table></div>
<h3>Acerto por tipo de caso</h3>
<div class="tw"><table class="mapa" id="mapa"></table></div>
<p class="cap">Cada célula mostra o acerto e o número de respostas certas. Há poucos casos por tipo (número entre parênteses), então estes valores indicam onde olhar, não bastam como prova. Selecionar uma célula abre o tipo no explorador.</p>
</section>

<section id="erros">
<h2><span class="n">4.</span>Análise de erros</h2>
<p class="lead">Cada resposta errada foi classificada pela causa. A contagem é de respostas, não de casos.</p>
<div class="tw"><table id="erros-t"></table></div>
<p id="leit-erros" style="margin-top:.8rem"></p>
</section>

<section id="iteracao" hidden>
<h2><span class="n">5.</span>Iteração de prompt: T4 v1 → v2</h2>
<p class="lead">O T4 v1 errou todos os casos do tipo valor_total. O T4 v2 muda o prompt em dois pontos e é medido nos mesmos 50 casos, com 3 repetições.</p>
<h3>O que mudou no prompt</h3>
<pre id="it-diff"></pre>
<h3>Resultado</h3>
<div class="tiles" id="it-tiles"></div>
<div class="nota" id="it-nota"></div>
<h3>Por tipo de caso</h3>
<div class="tw"><table id="it-tab"></table></div>
<p class="cap" id="it-cmp"></p>
</section>

<section id="explorador">
<h2><span class="n">6.</span>Explorador de casos</h2>
<p class="lead">Compara o gabarito com a resposta de cada técnica, campo a campo. Células em vermelho são divergências.</p>
<div class="ctl">
<div><label for="tipo">Tipo de caso</label><select id="tipo"></select></div>
<div><label for="caso">Caso</label><select id="caso"></select></div>
<div><label for="rep">Repetição</label><select id="rep"></select></div>
</div>
<div class="desc"><strong>O que este tipo testa:</strong> <span id="desctipo"></span></div>
<div id="detalhe"></div>
</section>

<section id="limitacoes">
<h2><span class="n">7.</span>Limitações e próximos passos</h2>
<ul class="lim" id="lim"></ul>
<h3>Próximos passos</h3>
<ol class="lim" id="prox"></ol>
<p class="cap">Perguntas de aprofundamento e decisões de projeto, com o estado de cada uma: <a class="lk" href="https://github.com/Prodigyb0y/prompt-engineering/blob/main/docs/LIMITACOES_E_DECISOES.md">docs/LIMITACOES_E_DECISOES.md</a>.</p>
</section>
</div>
<footer><div class="w">Código, dados, prompts, testes e relatórios: <a href="https://github.com/Prodigyb0y/prompt-engineering">github.com/Prodigyb0y/prompt-engineering</a>. Dados 100% fictícios. Projeto de portfólio, recriação conceitual sem dados reais.</div></footer>
<script id="dados" type="application/json">__DADOS__</script>
<script>
const D = JSON.parse(document.getElementById('dados').textContent);
const $ = id => document.getElementById(id);
const pct = x => (100*x).toFixed(1).replace('.',',')+'%';
const usd = x => x.toFixed(6).replace('.',',');
const seg = x => x.toFixed(2).replace('.',',');
const el = (t, txt, cls) => { const e=document.createElement(t); if(txt!==undefined) e.textContent=txt; if(cls) e.className=cls; return e; };
const R = D.resumo;
const nome = r => r.id+' · '+r.tecnica;
const nomeId = id => id+' · '+D.nomes[id];
$('aviso').textContent = D.aviso;

// ficha e números
$('ficha').append(...[['Objetivo',D.ficha.pergunta],['Método',D.ficha.metodo],['Resultado',D.veredito],['Principal limite',D.ficha.limite]].flatMap(([k,v])=>[el('dt',k),el('dd',v)]));
const tiles=$('tiles');
function tile(k,v,d){ const t=el('div',undefined,'tile'); t.appendChild(el('div',k,'k')); t.appendChild(el('div',v,'v')); t.appendChild(el('div',d,'d')); tiles.appendChild(t); }
const porAc=[...R].sort((a,b)=>a.acerto-b.acerto), porCu=[...R].sort((a,b)=>a.custo_caso-b.custo_caso), porLa=[...R].sort((a,b)=>a.lat-b.lat);
tile('Acerto por caso', pct(porAc[0].acerto)+' a '+pct(porAc[porAc.length-1].acerto), 'menor: '+nome(porAc[0])+'; maior: '+nome(porAc[porAc.length-1]));
tile('Custo por caso', 'US$ '+usd(porCu[0].custo_caso)+' a '+usd(porCu[porCu.length-1].custo_caso), 'menor: '+nome(porCu[0])+'; maior: '+nome(porCu[porCu.length-1]));
tile('Latência média', seg(porLa[0].lat)+' s a '+seg(porLa[porLa.length-1].lat)+' s', 'menor: '+nome(porLa[0])+'; maior: '+nome(porLa[porLa.length-1]));

// metodologia: técnicas
{ const t=$('t-tec'); const h=el('tr'); ['ID','Técnica','O que muda no prompt','Exemplos','Raciocínio antes da resposta','Onde ficam as regras'].forEach(c=>h.appendChild(el('th',c))); t.appendChild(h);
  R.forEach(r=>{ const tr=el('tr'); [r.id,r.tecnica,D.tecnicas[r.id].como,D.compara[0][1][r.id],D.compara[1][1][r.id],D.compara[2][1][r.id]].forEach(v=>tr.appendChild(el('td',v))); t.appendChild(tr); }); }
R.forEach(r=>{ const d=el('details'); d.appendChild(el('summary','Prompt '+r.id+' · '+r.tecnica+' ('+r.versao+', hash '+r.hash+')'));
  const p=D.prompts[r.id];
  if(p.system){ d.appendChild(el('span','System prompt','rot')); d.appendChild(el('pre',p.system)); }
  d.appendChild(el('span','Mensagem do usuário (o texto do caso substitui {texto})','rot')); d.appendChild(el('pre',p.user)); $('prompts').appendChild(d); });
{ const t=$('anat'); const h=el('tr'); ['Parte','Trecho do prompt','Função'].forEach(c=>h.appendChild(el('th',c))); t.appendChild(h);
  D.anatomia.forEach(([nm,trecho,fn])=>{ const tr=el('tr'); tr.appendChild(el('th',nm)); const td=el('td'); td.appendChild(el('pre',trecho)); tr.appendChild(td); tr.appendChild(el('td',fn)); t.appendChild(tr); });
  $('anat-nota').textContent=D.anatomia_nota; }
{ const t=$('t-met'); const h=el('tr'); ['Métrica','Definição','Como foi medida'].forEach(c=>h.appendChild(el('th',c))); t.appendChild(h);
  D.metricas.forEach(m=>{ const tr=el('tr'); m.forEach((v,i)=>tr.appendChild(el(i===0?'th':'td',v))); t.appendChild(tr); }); }

// barras
function barras(id, val, fmt, max, ic){
  const box=$(id);
  R.forEach(r=>{ const l=el('div',undefined,'barra'); l.appendChild(el('div',nome(r)));
    const t=el('div',undefined,'trilho'); const b=el('div',undefined,'pre'); b.style.width=(100*val(r)/max)+'%'; t.appendChild(b);
    if(ic){ const w=el('div',undefined,'ic'); w.style.left=(100*r.ic_lo/max)+'%'; w.style.width=(100*(r.ic_hi-r.ic_lo)/max)+'%'; t.appendChild(w); }
    l.appendChild(t); l.appendChild(el('div',fmt(r),'v')); box.appendChild(l); }); }
barras('g-acerto',r=>r.acerto,r=>pct(r.acerto),1,true);
barras('g-custo',r=>r.custo_caso,r=>usd(r.custo_caso),Math.max(...R.map(r=>r.custo_caso)),false);
barras('g-lat',r=>r.lat,r=>seg(r.lat),Math.max(...R.map(r=>r.lat)),false);

// iteração de prompt (só existe na rodada v2)
if(!D.iteracao){ document.querySelectorAll('a[href="#iteracao"]').forEach(a=>a.remove()); }
if(D.iteracao){
  const I=D.iteracao; $('iteracao').hidden=false;
  $('it-diff').textContent=I.diff.join('\\n');
  const vt=I.por_tipo.valor_total; const outros=Object.entries(I.por_tipo).filter(([k])=>k!=='valor_total');
  const so=(f,g)=>outros.reduce((a,[,x])=>a+x[f],0), sr=outros.reduce((a,[,x])=>a+x.respostas,0);
  const tl=(k,v,d)=>{ const t=el('div',undefined,'tile'); t.appendChild(el('div',k,'k')); t.appendChild(el('div',v,'v')); t.appendChild(el('div',d,'d')); $('it-tiles').appendChild(t); };
  tl('Acerto por caso',pct(I.acerto_v1)+' → '+pct(I.acerto_v2),'T4 v1 → T4 v2, média de 3 repetições');
  tl('Tipo valor_total',vt.certas_v1+' de '+vt.respostas+' → '+vt.certas_v2+' de '+vt.respostas_v2,'respostas certas, v1 → v2');
  tl('Demais tipos',so('certas_v1')+' de '+sr+' → '+so('certas_v2')+' de '+sr,I.piorou.length?('regressões: '+I.piorou.join(', ')):'sem regressão em nenhum caso');
  tl('Custo por resposta (US$)',usd(I.custo_v1)+' → '+usd(I.custo_v2),'tokens de saída médios: '+Math.round(I.tokens_saida_v1)+' → '+Math.round(I.tokens_saida_v2));
  $('it-nota').textContent='Atenção: a regra nova foi escrita depois de ver os erros nesses mesmos casos. O resultado mostra que a mudança corrige o problema e não quebra os outros tipos, mas não prova que vale para casos novos. Teste do sinal exato pareado: '+I.melhorou.length+' casos melhoraram, '+I.piorou.length+' pioraram, p = '+I.p_sinal.toFixed(3).replace('.',',')+'; com tão poucos casos discordantes o teste não chega a p < 0,05 mesmo com todos na mesma direção.';
  const t=$('it-tab'); const h=el('tr'); ['Tipo de caso','Casos','Respostas certas v1','Respostas certas v2'].forEach(c=>h.appendChild(el('th',c))); t.appendChild(h);
  Object.entries(I.por_tipo).forEach(([k,x])=>{ const tr=el('tr'); [(D.tipos[k]||[k])[0],String(x.casos),x.certas_v1+' de '+x.respostas,x.certas_v2+' de '+x.respostas_v2].forEach((v,i)=>tr.appendChild(el('td',v,i>0?'num':''))); t.appendChild(tr); });
  const t3=R.find(r=>r.id==='T3');
  if(t3) $('it-cmp').textContent='Para referência, na mesma rodada o T3 (chain-of-thought) teve acerto de '+pct(t3.acerto)+' a US$ '+usd(t3.custo_caso)+' por resposta; o T4 v2 teve '+pct(I.acerto_v2)+' a US$ '+usd(I.custo_v2)+', cerca de '+(I.custo_v2/t3.custo_caso*100).toFixed(0)+'% do custo do T3. O T3 não foi ajustado depois de ver os resultados e o T4 v2 foi, então a comparação não é simétrica.';
}

// comparações pareadas
{ const t=$('pares'); const h=el('tr'); ['Par','Casos a favor do primeiro','Casos a favor do segundo','Empates','p'].forEach(c=>h.appendChild(el('th',c))); t.appendChild(h);
  const nc=D.casos.length;
  D.pares.forEach(([a,b,fa,fb,p])=>{ const tr=el('tr'); [nomeId(a)+' × '+nomeId(b),String(fa),String(fb),String(nc-fa-fb),p.toFixed(3).replace('.',',')].forEach((v,i)=>tr.appendChild(el('td',v,i>0?'num':''))); t.appendChild(tr); }); }

// tabela completa
{ const tb=$('tabela'); const h=el('tr'); ['Técnica','Prompt','Acerto por caso','IC 95%','Mín–máx (3 repetições)','JSON válido','Tokens entrada (média)','Tokens saída (média)','Custo por caso (US$)','Custo por acerto (US$)','Latência média (s)'].forEach(c=>h.appendChild(el('th',c))); tb.appendChild(h);
  R.forEach(r=>{ const tr=el('tr');
    [nome(r), r.versao+' '+r.hash, pct(r.acerto), pct(r.ic_lo)+'–'+pct(r.ic_hi), pct(r.rep_min)+'–'+pct(r.rep_max), pct(r.jv), String(Math.round(r.tin)), String(Math.round(r.tout)), usd(r.custo_caso), usd(r.custo_acerto), seg(r.lat)]
     .forEach((v,i)=>tr.appendChild(el('td',v,i>=2?'num':''))); tb.appendChild(tr); }); }

// explorador
const st=$('tipo'), sc=$('caso'), sr=$('rep');
const tipos=[]; D.casos.forEach((c,i)=>{ let t=tipos.find(x=>x.tipo===c.tipo); if(!t){ t={tipo:c.tipo,idx:[]}; tipos.push(t);} t.idx.push(i); });
const nomeTipo = k => (D.tipos[k]||[k,''])[0];
const cls = v => v>=1?'h100':v>=0.9?'h90':v>=0.7?'h70':'h0';

// mapa
{ const mp=$('mapa'); const h=el('tr'); h.appendChild(el('th','Tipo de caso')); R.forEach(r=>h.appendChild(el('th',nome(r)))); mp.appendChild(h);
  tipos.forEach((t,k)=>{ const tr=el('tr'); tr.appendChild(el('td',nomeTipo(t.tipo)+' ('+t.idx.length+')'));
    R.forEach(r=>{ const v=D.por_tipo[r.id][t.tipo]; const n=t.idx.length*D.repeticoes, hit=Math.round(v*n); const td=el('td',undefined,'c '+cls(v)); td.appendChild(document.createTextNode(pct(v))); td.appendChild(el('small',hit+' de '+n));
      td.onclick=()=>{ st.value=k; trocarTipo(); $('explorador').scrollIntoView(); }; tr.appendChild(td); });
    mp.appendChild(tr); }); }

// erros
{ const t=$('erros-t'); const h=el('tr'); ['Técnica','Respostas erradas','Causa'].forEach(c=>h.appendChild(el('th',c))); t.appendChild(h);
  R.forEach(r=>{ const e=D.erros.por_tecnica[r.id]; const tr=el('tr'); tr.appendChild(el('td',nome(r)));
    tr.appendChild(el('td',e.total+' de '+e.respostas,'num'));
    tr.appendChild(el('td',Object.entries(e.classes).map(([k,n])=>n+' × '+(D.erros.rotulos[k]||k)).join('; ')||'—')); t.appendChild(tr); });
  $('leit-erros').textContent=D.erros.leitura; }

tipos.forEach((t,k)=>{ const o=el('option',nomeTipo(t.tipo)+' ('+t.idx.length+' '+(t.idx.length>1?'casos':'caso')+')'); o.value=k; st.appendChild(o); });
for(let i=1;i<=D.repeticoes;i++){ const o=el('option','Repetição '+i); o.value=i; sr.appendChild(o); }
const rotulo = c => { const g=c.gabarito; return String(g.quantidade).replace('.',',')+' '+g.unidade+' de '+g.item; };
const fmt = v => v===undefined?'—':JSON.stringify(v);
function trocarTipo(){
  const t=tipos[st.value]; sc.replaceChildren();
  t.idx.forEach(i=>{ const c=D.casos[i]; const o=el('option',c.id+' · '+rotulo(c)); o.value=i; sc.appendChild(o); });
  $('desctipo').textContent=(D.tipos[t.tipo]||['',''])[1]; mostrar();
}
function mostrar(){
  const c=D.casos[sc.value], rep=+sr.value, box=$('detalhe'); box.replaceChildren();
  box.appendChild(el('span','Texto da solicitação','rot')); box.appendChild(el('pre',c.texto));
  box.appendChild(el('span','Gabarito × resposta de cada técnica (repetição '+rep+')','rot'));
  const ts=Object.keys(c.saidas).sort();
  const wrap=el('div',undefined,'tw'); const t=el('table',undefined,'cmp');
  const h=el('tr'); h.appendChild(el('th','Campo')); h.appendChild(el('th','Gabarito')); ts.forEach(x=>h.appendChild(el('th',nomeId(x)))); t.appendChild(h);
  D.campos.forEach(f=>{ const tr=el('tr'); tr.appendChild(el('th',f)); tr.appendChild(el('td',fmt(c.gabarito[f])));
    ts.forEach(x=>{ const s=c.saidas[x][rep-1]; if(!s){ tr.appendChild(el('td','—')); return; }
      const ok=s.campos[f]===true; const v=s.parsed? fmt(s.parsed[f]) : '(JSON inválido)';
      tr.appendChild(el('td',v,ok?'ok':'erro')); }); t.appendChild(tr); });
  const rs=el('tr'); rs.appendChild(el('th','Resultado do caso')); rs.appendChild(el('td','—'));
  ts.forEach(x=>{ const s=c.saidas[x][rep-1]; rs.appendChild(el('td',s&&s.correto?'certo':'errado',s&&s.correto?'ok':'erro')); }); t.appendChild(rs);
  wrap.appendChild(t); box.appendChild(wrap);
  const erradas=ts.filter(x=>{ const s=c.saidas[x][rep-1]; return s && !s.correto; });
  if(erradas.length){ box.appendChild(el('span','Causa das divergências','rot'));
    erradas.forEach(x=>{ const s=c.saidas[x][rep-1]; const d=el('div',undefined,'por'); d.appendChild(el('b',nomeId(x))); d.appendChild(document.createTextNode(s.porque||'Campos diferentes do gabarito.')); box.appendChild(d); }); }
  const dd=el('details'); dd.appendChild(el('summary','Respostas brutas'));
  ts.forEach(x=>{ const s=c.saidas[x][rep-1]; if(!s) return; dd.appendChild(el('span',nomeId(x)+(s.classe&&s.classe!=='correto'?' · classe do erro: '+s.classe:''),'rot')); dd.appendChild(el('pre',s.resposta)); });
  box.appendChild(dd);
}
st.onchange=trocarTipo; sc.onchange=mostrar; sr.onchange=mostrar; trocarTipo();

// limitações
D.limitacoes.forEach(x=>$('lim').appendChild(el('li',x)));
D.prioridades.forEach(p=>{ const li=el('li'); li.appendChild(el('strong',p[0]+'. ')); li.appendChild(document.createTextNode(p[1])); $('prox').appendChild(li); });

// navegação: marca a seção visível
const links=[...document.querySelectorAll('#nav a')];
const obs=new IntersectionObserver(es=>{ es.forEach(e=>{ if(e.isIntersecting){ links.forEach(a=>a.classList.toggle('on',a.getAttribute('href')==='#'+e.target.id)); } }); },{rootMargin:'-20% 0px -70% 0px'});
document.querySelectorAll('section').forEach(s=>obs.observe(s));
</script></body></html>
"""


LINKS = {"v1": '<span class="seg on">Rodada v1</span><a class="seg" href="v2/index.html">Rodada v2</a>',
         "v2": '<a class="seg" href="../index.html">Rodada v1</a><span class="seg on">Rodada v2</span>'}
DESCRODADA = {"v1": "Primeira rodada: 50 casos de dificuldade moderada. Os erros se concentram num defeito do gerador de casos (ver Análise de erros).",
              "v2": "Segunda rodada: 50 casos sem o defeito da v1 e com tipos mais difíceis. Desenhada depois de conhecer o resultado da v1."}
ROTULOS_CLASSE = {
    "valor_nulo_sem_derivar": "valor total não dividido pela quantidade (devolveu null)",
    "fornecedor_ponto_final": "ponto final de \"Ltda.\" copiado do texto",
    "campo_diferente": "outro campo diferente do gabarito",
    "json_invalido": "JSON inválido",
    "schema_invalido": "schema inválido",
}
RELACAO_PROMPT = {
    "T1": "O prompt não diz o que fazer quando só há o valor total.",
    "T2": "Os 3 exemplos do prompt sempre trazem o preço unitário pronto; nenhum mostra um total a dividir.",
    "T3": "O prompt não traz regra para esse caso.",
    "T4": "O system prompt manda usar null quando a informação não está no texto e diz que, sem valor no texto, valor_unitario e moeda são null.",
}


def _fmt(v):
    return json.dumps(v, ensure_ascii=False)


def explicar(classe, obj, errados, g, tecnica):
    """Texto curto com o porquê de uma resposta errada (fatos do caso; a causa só é afirmada quando verificada)."""
    if classe == "valor_nulo_sem_derivar":
        total = round(g["valor_unitario"] * g["quantidade"], 2)
        t = f"{total:.2f}".replace(".", ",")
        extra = " e moeda = null" if obj.get("moeda") is None and g["moeda"] else ""
        return (f"O texto traz só o valor total ({g['moeda']} {t}). O gabarito pede o valor unitário: {t} ÷ {g['quantidade']} = "
                f"{_fmt(g['valor_unitario'])}. A resposta trouxe valor_unitario = null{extra}: o modelo tratou o dado como ausente em vez de calcular. "
                f"Relação com o prompt (fato do prompt; que ele causou o erro é hipótese): {RELACAO_PROMPT[tecnica]}")
    if classe == "fornecedor_ponto_final":
        return (f"A resposta trouxe {_fmt(obj.get('fornecedor'))} e o gabarito é {_fmt(g['fornecedor'])}: a diferença é um ponto final, copiado do texto "
                "porque o gerador de casos termina a frase logo após \"Ltda\". É defeito do conjunto de casos, não falta de compreensão da tarefa.")
    if classe in ("json_invalido", "schema_invalido"):
        return "O formato da resposta não passou na validação."
    return "Campos diferentes do gabarito: " + "; ".join(f"{c}: esperado {_fmt(g[c])}, veio {_fmt(obj.get(c)) if obj else 'sem JSON'}" for c in errados) + "."


def montar_anatomia():
    """Divide o system prompt do T4 v1 em partes e junta o texto real de cada parte à sua função (conteudo_demo.ANATOMIA)."""
    sistema = prompts_lib.carregar("T4", "v1")["system"]
    blocos = sistema.split("\n\n")
    regras = [l[2:] for l in blocos[2].splitlines()[1:]] if len(blocos) == 3 else []
    if len(regras) != len(ANATOMIA) - 2:
        raise SystemExit("O prompt T4 mudou de estrutura: atualize conteudo_demo.ANATOMIA.")
    trechos = [blocos[0], blocos[1]] + regras
    return [[nome, trecho, funcao] for (nome, funcao), trecho in zip(ANATOMIA, trechos)]


def montar_dados():
    resumo = json.loads((caminhos.RESULTADOS / "resumo.json").read_text(encoding="utf-8"))
    gab = json.loads((caminhos.DADOS / "gabarito.json").read_text(encoding="utf-8"))
    casos = json.loads((caminhos.DADOS / "casos_teste.json").read_text(encoding="utf-8"))
    regs = carregar(caminhos.RESULTADOS / "brutos")
    saidas = {}
    for r in regs:
        classe, _ = ce.classificar(r, gab[r["caso"]])
        obj, _ = vparse(r["resposta"], r["tecnica"])
        parsed = {k: obj.get(k) for k in CAMPOS if k in obj} if obj else None
        errados = [c for c, ok in r["avaliacao"].get("campos", {}).items() if not ok]
        porque = None if r["avaliacao"]["caso_correto"] else explicar(classe, obj, errados, gab[r["caso"]], r["tecnica"])
        saidas.setdefault(r["caso"], {}).setdefault(r["tecnica"], {})[r["repeticao"]] = {
            "resposta": r["resposta"].strip(), "correto": r["avaliacao"]["caso_correto"], "classe": classe,
            "parsed": parsed, "campos": r["avaliacao"].get("campos", {}), "porque": porque}
    ordenados = []
    for c in sorted(casos, key=lambda c: c["id"]):
        por_tec = {t: [reps[k] for k in sorted(reps)] for t, reps in saidas[c["id"]].items()}
        ordenados.append({"id": c["id"], "tipo": c["tipo"], "texto": c["texto"], "gabarito": gab[c["id"]], "saidas": por_tec})
    tabela = [{"id": t, "tecnica": r["tecnica"], "versao": r["prompt_versao"], "hash": r["prompt_hash12"],
               "acerto": r["acerto_caso_media"], "ic_lo": r["ic95_baixo"], "ic_hi": r["ic95_alto"],
               "rep_min": r["acerto_caso_rep_min"], "rep_max": r["acerto_caso_rep_max"],
               "custo_caso": r["custo_por_caso_usd"], "custo_acerto": r["custo_por_acerto_usd"],
               "lat": r["latencia_media_s"], "tin": r["tokens_entrada_media"], "tout": r["tokens_saida_media"],
               "jv": r["json_valido"]} for t, r in sorted(resumo.items())]
    nomes = {t: r["tecnica"] for t, r in resumo.items()}
    erros_total = sum(1 for r in regs if not r["avaliacao"]["caso_correto"])
    so_ponto = sum(1 for r in regs if ce.classificar(r, gab[r["caso"]])[0] == "fornecedor_ponto_final")
    if so_ponto:
        quantas = (f"As {erros_total} respostas erradas são todas" if erros_total == so_ponto
                   else f"{so_ponto} das {erros_total} respostas erradas são")
        aviso = (f"{quantas} o mesmo artefato do gerador de casos: o texto traz \"Ltda.\" e o modelo copiou o ponto, "
                 "mas o gabarito não tem ponto. Na recontagem pós-hoc (não oficial, feita depois de ver os resultados) as técnicas empatam, "
                 "então a tabela NÃO mostra qual técnica entende melhor a tarefa. A diferença que sobra é de custo e latência. "
                 "Nenhum par atende ao critério de diferença.")
    else:
        pares = separaveis(resumo)
        nomes_t = {t: f"{t} {r['tecnica']}" for t, r in resumo.items()}
        if pares:
            aviso = ("Com intervalos de 95% sem sobreposição e teste do sinal exato com p < 0,05, pode-se declarar: "
                     + "; ".join(f"{nomes_t[a]} acerta mais que {nomes_t[b]}" for a, b in pares)
                     + ". Para os demais pares não há vencedor declarado.")
        else:
            aviso = ("Nenhuma técnica é declarada melhor: nenhum par atende ao critério (intervalos de 95% sem sobreposição e teste do sinal exato "
                     "pareado com p < 0,05). Quando uma técnica acerta 100% dos casos, o intervalo bootstrap tem largura zero e não basta sozinho.")
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
    pares_ok = separaveis(resumo)
    if pares_ok:
        veredito = ("Resultado oficial: " + "; ".join(f"{a} {nomes[a]} acerta mais que {b} {nomes[b]}" for a, b in pares_ok)
                    + " (intervalos sem sobreposição e p < 0,05). Para os demais pares não há vencedor declarado. Veja a seção Análise de erros.")
    else:
        veredito = ("Nenhuma técnica é declarada melhor: nenhum par atende ao critério (intervalos de 95% sem sobreposição e teste do sinal exato pareado "
                    "com p < 0,05). Veja a tabela de comparações na seção Resultados.")
    te = {r["tipo"] for r in regs if not r["avaliacao"]["caso_correto"]}
    if pares_ok and len(te) == 1:
        veredito += (f" Atenção: todo o erro está num único tipo de caso (\"{next(iter(te))}\"), então a diferença mostra como cada prompt trata um dado "
                     "que o texto não traz pronto, e não uma superioridade geral.")
    por_tec = {t: {"total": 0, "respostas": 0, "classes": {}} for t in resumo}
    for r in regs:
        e = por_tec[r["tecnica"]]
        e["respostas"] += 1
        if not r["avaliacao"]["caso_correto"]:
            e["total"] += 1
            cl = ce.classificar(r, gab[r["caso"]])[0]
            e["classes"][cl] = e["classes"].get(cl, 0) + 1
    classes_vistas = {c for e in por_tec.values() for c in e["classes"]}
    reps = max(r["repeticoes"] for r in resumo.values())
    if classes_vistas == {"fornecedor_ponto_final"}:
        leitura = (f"As {erros_total} respostas erradas têm a mesma causa: o texto traz \"Ltda.\" e o modelo copiou o ponto final, que o gabarito não tem. "
                   "É um defeito do gerador de casos (ele termina a frase logo depois da abreviação), não falta de compreensão da tarefa: na recontagem pós-hoc, sem o ponto, as técnicas empatam. "
                   "A contagem difere entre técnicas porque cada uma copia o ponto numa frequência diferente; hipótese, não testada: o T4 tem a regra \"copie o nome como aparece no texto\", o que pode levá-lo a copiar mais. "
                   "Por isso a rodada v2 foi criada, sem esse defeito.")
        limite = (f"Todas as {erros_total} respostas erradas vêm de um defeito do gerador de casos, não de falta de compreensão da tarefa. O resultado oficial foi mantido e a "
                  "recontagem sem o defeito está marcada como pós-hoc. Ver a seção Limitações.")
    elif classes_vistas == {"valor_nulo_sem_derivar"}:
        n_tipo = sum(1 for c in casos if c["tipo"] == "valor_total") * reps
        errou = {t: sum(1 for r in regs if r["tecnica"] == t and r["tipo"] == "valor_total" and not r["avaliacao"]["caso_correto"]) for t in resumo}
        partes = "; ".join(f"{t} {nomes[t]}: {errou[t]} de {n_tipo}" for t in sorted(errou))
        leitura = (f"Todo o erro está no tipo valor_total, onde o texto traz só o valor total e o gabarito exige dividir pela quantidade. Respostas erradas nesse tipo: {partes}. "
                   "Em todas, o modelo devolveu valor_unitario = null em vez de calcular.")
        if errou.get("T1", 0) < errou.get("T2", 0) and errou.get("T1", 0) < errou.get("T4", 0):
            leitura += (" Mais instruções não significaram mais acerto aqui: a técnica sem exemplos nem regras (T1) errou menos que a com exemplos (T2) e a com regras (T4). "
                        "Hipótese, não testada: os 3 exemplos do T2 sempre trazem o preço unitário pronto, e o T4 manda usar null quando o dado não está no texto; "
                        "ambos podem ter ensinado o modelo a não calcular.")
        limite = (f"Todas as {erros_total} respostas erradas estão no tipo valor_total, onde a conta que o gabarito exige (total ÷ quantidade) não está escrita em nenhum prompt. "
                  "Esse ponto mede como cada prompt trata uma informação implícita, não quem entende melhor a tarefa. Ver a seção Limitações.")
    else:
        leitura = "As respostas erradas têm mais de uma causa; veja a classificação acima e o explorador de casos."
        limite = "Há erros de mais de um tipo; ver a seção Resultados."
    ficha = {"pergunta": "Qual técnica de prompt extrai melhor os dados de pedidos de compra escritos em texto livre, e quanto custa cada acerto?",
             "metodo": (f"{len(casos)} pedidos fictícios, com gabarito escrito e congelado antes de rodar. Cada uma das 4 técnicas respondeu a cada caso {reps} vezes "
                        f"({len(regs)} respostas nesta rodada). Um caso só conta como certo se os 8 campos baterem com o gabarito. Modelo: claude-haiku-5-5."),
             "limite": limite}
    n_dif = len({r["caso"] for r in regs if not r["avaliacao"]["caso_correto"]})
    itens = {g["item"] for g in gab.values()}
    forn = {g["fornecedor"] for g in gab.values() if g["fornecedor"]}
    dinamicas = [f"Poder de discriminação baixo: só {n_dif} dos {len(casos)} casos têm alguma resposta errada em alguma técnica; os demais são acertados por todas. "
                 "Toda a diferença entre técnicas depende desses poucos casos.",
                 f"Pouca variedade: {len(itens)} itens e {len(forn)} fornecedores distintos nos {len(casos)} casos, e os exemplos do T2 compartilham itens e fornecedores com parte dos casos de teste "
                 "(contagens em resultados/AUDITORIA.md)."]
    it_arq = caminhos.RESULTADOS / "iteracao.json"
    iteracao = json.loads(it_arq.read_text(encoding="utf-8")) if it_arq.exists() else None
    return {"iteracao": iteracao, "anatomia": montar_anatomia(), "anatomia_nota": ANATOMIA_NOTA,
            "pares": [[a, b, fa, fb, p] for a, b, fa, fb, p in comparacoes(resumo)], "ficha": ficha, "metricas": [list(m) for m in METRICAS], "limitacoes": LIMITACOES + dinamicas + [limite], "prioridades": [list(x) for x in PRIORIDADES],
            "erros": {"por_tecnica": por_tec, "rotulos": ROTULOS_CLASSE, "leitura": leitura},
            "veredito": veredito, "campos": CAMPOS, "compara": [[k, v] for k, v in COMPARA],
            "por_tipo": {t: r["acerto_tipo"] for t, r in resumo.items()},
            "tipos": {k: list(v) for k, v in TIPOS.items()}, "tecnicas": {k: {"como": TECNICAS[k]["como"]} for k in resumo},
            "prompts": prompts, "resumo": tabela, "nomes": nomes, "casos": ordenados, "repeticoes": max(r["repeticoes"] for r in resumo.values()),
            "aviso": aviso, "notas": notas}


def main():
    dados = montar_dados()
    blob = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    destino = caminhos.DOCS
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "index.html").write_text(TEMPLATE.replace("__LINKS__", LINKS[caminhos.VERSAO]).replace("__DESCRODADA__", DESCRODADA[caminhos.VERSAO]).replace("__VERSAO__", caminhos.VERSAO).replace("__DADOS__", blob), encoding="utf-8", newline="\n")
    if caminhos.VERSAO == "v1":
        linhas = ["# Limitações e decisões de projeto", "",
                  "Perguntas de aprofundamento sobre o método, com a resposta, o que mudar e o estado de cada ponto. "
                  "Gerado por `src/gerar_demo.py` a partir de `src/conteudo_demo.py`.", ""]
        for i, (q, r, m, e) in enumerate(QA, 1):
            linhas += [f"## {i}. {q}", "", f"**Estado:** {e}", "", f"**Resposta honesta:** {r}", "", f"**O que mudar:** {m}", ""]
        linhas += ["## O que eu mudaria, em ordem", ""] + [f"{i}. **{t}.** {w}" for i, (t, w) in enumerate(PRIORIDADES, 1)] + [""]
        (RAIZ / "docs" / "LIMITACOES_E_DECISOES.md").write_text("\n".join(linhas), encoding="utf-8", newline="\n")
    print(f"{destino}/index.html gerado ({caminhos.VERSAO}): {len(dados['casos'])} casos, {len(dados['resumo'])} técnicas")


if __name__ == "__main__":
    main()
