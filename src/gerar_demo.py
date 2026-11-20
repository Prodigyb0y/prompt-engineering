"""P11: gera docs/index.html (página estática, sem servidor e sem chave) a partir dos resultados.

Lê resultados/brutos/*.json, resultados/resumo.json, dados/*.json. Nada é digitado à mão:
todo número da página vem de resumo.json. Os dados dos casos vão embutidos no HTML.

Uso: python src/gerar_demo.py
"""
import json
from pathlib import Path

import caminhos
from conteudo_demo import GLOSSARIO, PRIORIDADES, QA
import classificar_erros as ce
from analisar import carregar, separaveis
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
<title>Laboratório de prompt engineering</title>
<style>
:root{--tx:#1c2433;--mut:#5b6678;--bg:#f5f7fb;--card:#fff;--bd:#d9dfea;--ac:#4a3fd6;--acl:#eef0fb;--ok:#1f7a3d;--okl:#e3f4e8;--er:#b3261e;--erl:#fbe7e5;--av:#fff6df}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;color:var(--tx);background:var(--bg)}
main{max-width:1000px;margin:0 auto;padding:0 1rem 3rem}
header{background:linear-gradient(135deg,#2a2370,#4a3fd6);color:#fff;padding:1.6rem 1rem 1.4rem}
header .in{max-width:1000px;margin:0 auto}
header h1{margin:.1rem 0 .4rem;font-size:1.7rem;line-height:1.2}
header p{margin:.3rem 0;max-width:46rem;opacity:.95}
header a{color:#fff;text-decoration:underline}
.chips{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.7rem}
.chip{background:rgba(255,255,255,.18);border-radius:99px;padding:.1rem .7rem;font-size:.82rem}
nav{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid var(--bd);box-shadow:0 1px 4px rgba(0,0,0,.05)}
nav .in{max-width:1000px;margin:0 auto;display:flex;overflow-x:auto}
nav button{flex:1 0 auto;border:0;background:none;padding:.8rem 1rem;font:inherit;font-weight:600;color:var(--mut);cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap}
nav button[aria-selected=true]{color:var(--ac);border-bottom-color:var(--ac)}
h2{font-size:1.3rem;margin:1.8rem 0 .2rem}
h2+.sub{color:var(--mut);margin:0 0 1rem}
h3{font-size:1rem;margin:1.1rem 0 .3rem}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:1rem 1.1rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.9rem}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:.8rem;margin:1.2rem 0 .6rem}
.tile{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:.8rem 1rem}
.tile .k{font-size:.78rem;font-weight:700;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.tile .v{font-size:1.45rem;font-weight:700;line-height:1.25;margin:.15rem 0}
.tile .d{font-size:.85rem;color:var(--mut)}
.verd{background:var(--acl);border-left:4px solid var(--ac);border-radius:6px;padding:.6rem .9rem;margin:.4rem 0 .2rem}
.aviso{background:var(--av);border:1px solid #e3c875;border-radius:10px;padding:.8rem 1rem}
.tec h3{margin:.1rem 0;font-size:1.1rem}
.tec .ap{color:var(--ac);font-weight:600;font-size:.9rem}
.tec p{margin:.35rem 0}
.tec .met{background:var(--acl);border-radius:8px;padding:.45rem .6rem;font-size:.88rem;margin-top:.6rem}
.rot{font-weight:700;font-size:.78rem;color:var(--mut);text-transform:uppercase;letter-spacing:.04em;display:block;margin-top:.55rem}
details{margin-top:.6rem}summary{cursor:pointer;color:var(--ac);font-weight:600;font-size:.9rem}
pre{white-space:pre-wrap;word-break:break-word;background:#f1f3f8;padding:.6rem;border-radius:8px;font-size:.8rem;margin:.4rem 0;line-height:1.45}
table{border-collapse:collapse;width:100%;font-size:.86rem;background:var(--card)}
th,td{border:1px solid var(--bd);padding:.4rem .55rem;text-align:left;vertical-align:top}th{background:#eceff6}
.num{text-align:right;font-variant-numeric:tabular-nums}
.ctl{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.8rem;margin-bottom:.8rem}
.ctl label{font-weight:700;font-size:.85rem;display:block}
select{width:100%;font-size:1rem;padding:.5rem;border:1px solid var(--bd);border-radius:8px;background:#fff;margin-top:.2rem;color:var(--tx)}
.desc{background:var(--acl);border-left:4px solid var(--ac);border-radius:6px;padding:.6rem .8rem;margin:.4rem 0 1rem}
.tag{font-weight:700;font-size:.85rem}.tag.ok{color:var(--ok)}.tag.erro{color:var(--er)}
.legenda{color:var(--mut);font-size:.88rem}.nota{color:var(--mut);font-size:.88rem}
.barra{display:grid;grid-template-columns:minmax(110px,170px) 1fr 5.5rem;gap:.6rem;align-items:center;margin:.35rem 0;font-size:.9rem}
.trilho{position:relative;height:22px;background:#e8ebf3;border-radius:5px}
.pre{position:absolute;left:0;top:0;bottom:0;background:var(--ac);border-radius:5px;opacity:.85}
.ic{position:absolute;top:50%;height:2px;background:#111;transform:translateY(-50%)}
.ic::before,.ic::after{content:"";position:absolute;top:-5px;width:2px;height:12px;background:#111}.ic::before{left:0}.ic::after{right:0}
.barra .v{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
.mapa td.c{text-align:center;font-variant-numeric:tabular-nums;cursor:pointer;font-weight:600}
.mapa .h100{background:var(--okl);color:var(--ok)}.mapa .h90{background:#f3f7d9}.mapa .h70{background:var(--av)}.mapa .h0{background:var(--erl);color:var(--er)}
.cmp td.ok{background:var(--okl)}.cmp td.erro{background:var(--erl);color:var(--er);font-weight:600}
.cmp td,.cmp th{font-size:.82rem;font-family:ui-monospace,Menlo,Consolas,monospace}.cmp th{font-family:inherit}
.passos{counter-reset:p;list-style:none;padding:0;margin:0}
.passos li{counter-increment:p;position:relative;padding:.3rem 0 .3rem 2.3rem}
.passos li::before{content:counter(p);position:absolute;left:0;top:.3rem;width:1.6rem;height:1.6rem;border-radius:50%;background:var(--ac);color:#fff;font-weight:700;font-size:.85rem;text-align:center;line-height:1.6rem}
[hidden]{display:none!important}
.legT{font-size:.88rem;margin-top:1.2rem;padding:.7rem 1rem}
.legT b{color:var(--ac)}
.ficha{display:grid;grid-template-columns:150px 1fr;gap:.5rem 1rem;margin:0}
.ficha dt{font-weight:700;color:var(--mut);font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;padding-top:.15rem}
.ficha dd{margin:0}
.qa{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:.2rem 1rem;margin:.6rem 0}
.qa summary{padding:.6rem 0;color:var(--tx);font-size:1rem}
.qa .r,.qa .m{margin:.2rem 0 .8rem}
.badge{display:inline-block;font-size:.72rem;font-weight:700;border-radius:99px;padding:.05rem .55rem;margin-left:.4rem;background:#e8ebf3;color:var(--mut);vertical-align:middle}
.badge.nf{background:var(--erl);color:var(--er)}.badge.ok{background:var(--okl);color:var(--ok)}
.por{border-left:4px solid var(--er);background:var(--erl);border-radius:6px;padding:.5rem .8rem;margin:.5rem 0;font-size:.9rem}
.por b{display:block}
dl.gl{margin:0}dl.gl dt{font-weight:700;margin-top:.7rem}dl.gl dd{margin:.1rem 0 0;color:#333}
.mapa small{display:block;font-weight:400;font-size:.72rem;opacity:.85}
@media(max-width:560px){.ficha{grid-template-columns:1fr}.ficha dd{margin-bottom:.5rem}header h1{font-size:1.4rem}.barra{grid-template-columns:90px 1fr 4.6rem}}
</style></head><body>
<header><div class="in">
<h1>Laboratório de prompt engineering</h1>
<p><strong>Mesma tarefa, mesmos casos, quatro técnicas de prompt: o que acerta mais, e quanto custa cada acerto.</strong></p>
<div class="chips"><span class="chip">Modelo: claude-haiku-5-5</span><span class="chip">50 casos · 4 técnicas · 3 repetições</span><span class="chip">Dados 100% fictícios (conjunto __VERSAO__)</span></div>
<p style="margin-top:.7rem"><a href="__OUTRA__">__OUTRA_TXT__</a></p>
</div></header>
<nav><div class="in" role="tablist">
<button role="tab" data-aba="entender">1 · Entender</button>
<button role="tab" data-aba="tecnicas">2 · As técnicas</button>
<button role="tab" data-aba="resultados">3 · Resultados</button>
<button role="tab" data-aba="explorar">4 · Explorar casos</button>
<button role="tab" data-aba="limites">5 · Limites e perguntas</button>
<button role="tab" data-aba="glossario">6 · Glossário</button>
</div></nav>
<main>
<section aria-label="Resumo">
<div class="card legT" id="leg"></div>
<h2>Ficha do estudo</h2>
<dl class="ficha card" id="ficha"></dl>
<h2>Em números</h2>
<div class="tiles" id="tiles"></div>
</section>

<section id="p-entender" role="tabpanel" hidden>
<h2>O que é um prompt?</h2>
<p class="sub">Em uma frase: prompt é a instrução que você escreve para a IA.</p>
<div class="card">
<p style="margin-top:0">Pense na IA como um profissional muito rápido que não conhece o seu contexto. O que ele entrega depende de como você pede: o que fazer, em que formato, com quais regras e se há exemplos de um bom resultado. Esse texto de pedido é o <strong>prompt</strong>.</p>
<p>A tarefa deste laboratório serve para qualquer área: alguém escreve um pedido de compra em texto livre (como num e-mail) e o sistema precisa transformar isso em dados organizados. Um advogado faria o mesmo com cláusulas de contratos, e um time de RH, com currículos.</p>
<span class="rot">Entrada: texto livre</span>
<pre>Oi, preciso de 25cx de etiqueta adesiva para Compras. R$ 2450,75 cada, com a Distribuidora Pinheiro, até 17-ago-2026.</pre>
<span class="rot">Saída esperada: dados organizados</span>
<pre>area: Compras · item: etiqueta adesiva · quantidade: 25 · unidade: cx
valor unitário: 2450.75 · moeda: BRL · fornecedor: Distribuidora Pinheiro · prazo: 2026-08-17</pre>
</div>
<h2>Por que engenharia de prompt?</h2>
<p class="sub">É escolher e testar a forma de pedir, em vez de confiar na primeira tentativa.</p>
<div class="grid">
<div class="card"><strong>Resposta no formato certo</strong><p>Sem instrução, a IA responde em texto solto. Com o formato definido, devolve dados que um sistema lê sem retrabalho humano.</p></div>
<div class="card"><strong>Menos erro nos casos difíceis</strong><p>Regras claras dizem o que fazer quando falta dado, o valor vem em outro formato ou o texto é confuso.</p></div>
<div class="card"><strong>Custo e velocidade sob controle</strong><p>Cada técnica gasta uma quantidade diferente de texto (tokens) e demora um tempo diferente. Dá para escolher a que compensa.</p></div>
<div class="card"><strong>Resultado que se pode auditar</strong><p>Com prompt versionado e gabarito fixo, qualquer pessoa confere se a mudança melhorou de verdade.</p></div>
</div>
<p class="nota">Esses são os motivos para medir, não uma promessa: este teste usa um modelo e 50 casos e não prova o mesmo para outras tarefas.</p>
<h2>Como usar esta página</h2>
<ol class="passos card">
<li>Veja o <strong>resumo</strong> no topo: acerto, custo e velocidade das quatro técnicas.</li>
<li>Na aba <strong>As técnicas</strong>, leia o que cada uma faz e o prompt real usado.</li>
<li>Na aba <strong>Resultados</strong>, veja os gráficos e o mapa de acerto por tipo de caso.</li>
<li>Na aba <strong>Explorar casos</strong>, compare lado a lado o que cada técnica respondeu com a resposta certa.</li>
</ol>
</section>

<section id="p-tecnicas" role="tabpanel" hidden>
<h2>As quatro técnicas comparadas</h2>
<p class="sub">Todas recebem os mesmos 50 textos e devolvem o mesmo JSON. Só muda a forma de pedir.</p>
<div class="grid" id="tecnicas"></div>
<h2>Diferenças em uma tabela</h2>
<div style="overflow-x:auto"><table id="compara"></table></div>
<p class="nota">Tokens são pedaços de texto cobrados pela API; a média é por resposta, nos casos rodados.</p>
</section>

<section id="p-resultados" role="tabpanel" hidden>
<h2>Leitura honesta do resultado</h2>
<div class="aviso"><span id="aviso"></span></div>
<h2>De onde vêm os erros</h2>
<p class="sub">Cada resposta errada foi classificada pela causa. Contagem de respostas, não de casos.</p>
<div style="overflow-x:auto"><table id="erros"></table></div>
<p id="leit-erros" style="margin-top:.8rem"></p>
<h2>Acerto por caso</h2>
<p class="sub">Maior é melhor. A barra preta mostra o intervalo de confiança de 95%: se duas faixas se sobrepõem, não dá para dizer que uma técnica é melhor que a outra.</p>
<div id="g-acerto"></div>
<h2>Custo por caso (US$)</h2>
<p class="sub">Menor é melhor. Tokens informados pela API × preço de tabela.</p>
<div id="g-custo"></div>
<h2>Latência média por chamada (s)</h2>
<p class="sub">Menor é melhor. Tempo medido com time.perf_counter.</p>
<div id="g-lat"></div>
<h2>Onde cada técnica acerta ou erra</h2>
<p class="sub">Acerto por tipo de caso, com a contagem de respostas certas. Cada tipo tem poucos casos: leia como pista, não como prova. Toque numa célula para abrir o tipo no explorador.</p>
<div style="overflow-x:auto"><table class="mapa" id="mapa"></table></div>
<p class="legenda">Verde: 100%. Amarelo-claro: 90% ou mais. Amarelo: 70% ou mais. Vermelho: abaixo de 70%. O número sempre aparece, a cor só ajuda.</p>
<h2>Tabela completa</h2>
<details open><summary>Mostrar ou esconder</summary>
<div style="overflow-x:auto"><table id="tabela"></table></div>
<p class="legenda"><strong>Acerto por caso</strong>: o caso só conta se os 8 campos estiverem certos. <strong>Custo por acerto</strong>: gasto total dividido pelos casos certos.</p></details>
<h2>Como foi medido</h2>
<p class="nota" id="notas"></p>
</section>

<section id="p-explorar" role="tabpanel" hidden>
<h2>Explorador de casos</h2>
<p class="sub">Escolha um tipo, depois um exemplo. A tabela compara a resposta certa com a de cada técnica; células vermelhas são erros.</p>
<div class="ctl">
<div><label for="tipo">1. Tipo de caso</label><select id="tipo"></select></div>
<div><label for="caso">2. Exemplo</label><select id="caso"></select></div>
<div><label for="rep">3. Repetição</label><select id="rep"></select></div>
</div>
<div class="desc"><strong>O que este tipo testa:</strong> <span id="desctipo"></span></div>
<div id="detalhe"></div>
<p class="nota">Cada caso foi rodado 3 vezes por técnica, porque o modelo pode variar de uma vez para outra.</p>
</section>

<section id="p-limites" role="tabpanel" hidden>
<h2>Limites do estudo e perguntas difíceis</h2>
<p class="sub">Perguntas que um entrevistador técnico faria, com a resposta honesta e o que mudaria. Toque numa pergunta para abrir.</p>
<div id="qa"></div>
<h2>O que eu mudaria, em ordem</h2>
<ol class="passos card" id="prior"></ol>
</section>

<section id="p-glossario" role="tabpanel" hidden>
<h2>Glossário</h2>
<p class="sub">Siglas e termos técnicos usados nesta página.</p>
<div id="gloss"></div>
</section>
</main>
<script id="dados" type="application/json">__DADOS__</script>
<script>
const D = JSON.parse(document.getElementById('dados').textContent);
const $ = id => document.getElementById(id);
const pct = x => (100*x).toFixed(1).replace('.',',')+'%';
const usd = x => x.toFixed(6).replace('.',',');
const seg = x => x.toFixed(2).replace('.',',');
const el = (t, txt, cls) => { const e=document.createElement(t); if(txt!==undefined) e.textContent=txt; if(cls) e.className=cls; return e; };
const R = D.resumo;
const nome = r => r.id+' '+D.tecnicas[r.id].apelido;
$('aviso').textContent = D.aviso; $('notas').textContent = D.notas;

// abas
const abas=['entender','tecnicas','resultados','explorar','limites','glossario'];
function abrir(a){ if(!abas.includes(a)) a='entender';
  abas.forEach(x=>{ $('p-'+x).hidden = x!==a; });
  document.querySelectorAll('nav button').forEach(b=>b.setAttribute('aria-selected', b.dataset.aba===a));
  try{ history.replaceState(null,'','#'+a); }catch(e){} }
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{ abrir(b.dataset.aba); window.scrollTo({top:0}); });

// legenda e ficha
{ const l=$('leg'); l.appendChild(el('b','Siglas: ')); R.forEach((r,i)=>{ l.appendChild(document.createTextNode((i?' · ':'')+r.id+' = '+r.tecnica+' (“'+D.tecnicas[r.id].apelido.toLowerCase()+'”)')); });
  l.appendChild(document.createTextNode('. '));
  const a=el('a','Glossário completo'); a.href='#glossario'; a.onclick=e=>{ e.preventDefault(); abrir('glossario'); window.scrollTo({top:0}); }; l.appendChild(a); }
$('ficha').append(...[['Pergunta',D.ficha.pergunta],['Método',D.ficha.metodo],['Achado',D.veredito],['Principal limite',D.ficha.limite]].flatMap(([k,v])=>[el('dt',k),el('dd',v)]));
// resumo
const tiles=$('tiles');
function tile(k,v,d){ const t=el('div',undefined,'tile'); t.appendChild(el('div',k,'k')); t.appendChild(el('div',v,'v')); t.appendChild(el('div',d,'d')); tiles.appendChild(t); }
const porAc=[...R].sort((a,b)=>a.acerto-b.acerto), porCu=[...R].sort((a,b)=>a.custo_caso-b.custo_caso), porLa=[...R].sort((a,b)=>a.lat-b.lat);
tile('Acerto por caso', pct(porAc[0].acerto)+' a '+pct(porAc[porAc.length-1].acerto), 'menor: '+nome(porAc[0])+' · maior: '+nome(porAc[porAc.length-1]));
tile('Custo por caso', 'US$ '+usd(porCu[0].custo_caso)+' a '+usd(porCu[porCu.length-1].custo_caso), 'mais barato: '+nome(porCu[0])+' · mais caro: '+nome(porCu[porCu.length-1]));
tile('Latência média', seg(porLa[0].lat)+' s a '+seg(porLa[porLa.length-1].lat)+' s', 'mais rápido: '+nome(porLa[0])+' · mais lento: '+nome(porLa[porLa.length-1]));

// técnicas
const tec=$('tecnicas');
R.forEach(r=>{
  const i=D.tecnicas[r.id]; const c=el('div',undefined,'card tec');
  c.appendChild(el('span',r.id+' · '+r.tecnica,'ap')); c.appendChild(el('h3',i.apelido)); c.appendChild(el('p',i.analogia));
  [['Como funciona aqui',i.como],['Quando costuma ajudar',i.quando],['Limite',i.limite]].forEach(([k,v])=>{ c.appendChild(el('span',k,'rot')); c.appendChild(el('p',v)); });
  c.appendChild(el('div','Neste teste: acerto '+pct(r.acerto)+' · custo por caso US$ '+usd(r.custo_caso)+' · latência média '+seg(r.lat)+' s','met'));
  const d=el('details'); d.appendChild(el('summary','Ver o prompt real ('+r.versao+', hash '+r.hash+')'));
  const p=D.prompts[r.id];
  if(p.system){ d.appendChild(el('span','System prompt','rot')); d.appendChild(el('pre',p.system)); }
  d.appendChild(el('span','Mensagem enviada (o texto do caso entra no lugar de {texto})','rot')); d.appendChild(el('pre',p.user));
  c.appendChild(d); tec.appendChild(c); });
const cp=$('compara'); { const h=el('tr'); h.appendChild(el('th','')); R.forEach(r=>h.appendChild(el('th',nome(r)))); cp.appendChild(h);
  D.compara.forEach(([k,m])=>{ const tr=el('tr'); tr.appendChild(el('th',k)); R.forEach(r=>tr.appendChild(el('td',m[r.id]))); cp.appendChild(tr); });
  [['Tokens de entrada (média)',r=>String(Math.round(r.tin))],['Tokens de saída (média)',r=>String(Math.round(r.tout))],['JSON válido',r=>pct(r.jv)]].forEach(([k,f])=>{
    const tr=el('tr'); tr.appendChild(el('th',k)); R.forEach(r=>tr.appendChild(el('td',f(r),'num'))); cp.appendChild(tr); }); }

// erros por técnica e causa
{ const t=$('erros'); const h=el('tr'); ['Técnica','Respostas erradas','Causa'].forEach(c=>h.appendChild(el('th',c))); t.appendChild(h);
  R.forEach(r=>{ const e=D.erros.por_tecnica[r.id]; const tr=el('tr'); tr.appendChild(el('td',nome(r)));
    tr.appendChild(el('td',e.total+' de '+e.respostas,'num'));
    const causas=Object.entries(e.classes).map(([k,n])=>n+' × '+(D.erros.rotulos[k]||k)).join('; ');
    tr.appendChild(el('td',causas||'—')); t.appendChild(tr); });
  $('leit-erros').textContent=D.erros.leitura; }

// gráficos de barras
function barras(id, val, fmt, max, ic){
  const box=$(id);
  R.forEach(r=>{ const l=el('div',undefined,'barra'); l.appendChild(el('div',nome(r)));
    const t=el('div',undefined,'trilho'); const b=el('div',undefined,'pre'); b.style.width=(100*val(r)/max)+'%'; t.appendChild(b);
    if(ic){ const w=el('div',undefined,'ic'); w.style.left=(100*r.ic_lo/max)+'%'; w.style.width=(100*(r.ic_hi-r.ic_lo)/max)+'%'; t.appendChild(w); }
    l.appendChild(t); l.appendChild(el('div',fmt(r),'v')); box.appendChild(l); }); }
barras('g-acerto',r=>r.acerto,r=>pct(r.acerto),1,true);
barras('g-custo',r=>r.custo_caso,r=>usd(r.custo_caso),Math.max(...R.map(r=>r.custo_caso)),false);
barras('g-lat',r=>r.lat,r=>seg(r.lat),Math.max(...R.map(r=>r.lat)),false);

// tabela completa
const tb=$('tabela');
{ const h=el('tr'); ['Técnica','Prompt','Acerto por caso','IC 95%','Mín–máx entre repetições','Custo por caso (US$)','Custo por acerto (US$)','Latência média (s)'].forEach(c=>h.appendChild(el('th',c))); tb.appendChild(h);
  R.forEach(r=>{ const tr=el('tr');
    [nome(r), r.versao+' '+r.hash, pct(r.acerto), pct(r.ic_lo)+'–'+pct(r.ic_hi), pct(r.rep_min)+'–'+pct(r.rep_max), usd(r.custo_caso), usd(r.custo_acerto), seg(r.lat)]
     .forEach((v,i)=>tr.appendChild(el('td',v,i>=2?'num':''))); tb.appendChild(tr); }); }

// explorador (variáveis antes do mapa, que usa trocarTipo)
const st=$('tipo'), sc=$('caso'), sr=$('rep');
const tipos=[]; D.casos.forEach((c,i)=>{ let t=tipos.find(x=>x.tipo===c.tipo); if(!t){ t={tipo:c.tipo,idx:[]}; tipos.push(t);} t.idx.push(i); });
const nomeTipo = k => (D.tipos[k]||[k,''])[0];
const cls = v => v>=1?'h100':v>=0.9?'h90':v>=0.7?'h70':'h0';

// mapa tipos x técnicas
const mp=$('mapa'); { const h=el('tr'); h.appendChild(el('th','Tipo de caso')); R.forEach(r=>h.appendChild(el('th',nome(r)))); mp.appendChild(h);
  tipos.forEach((t,k)=>{ const tr=el('tr'); tr.appendChild(el('td',nomeTipo(t.tipo)+' ('+t.idx.length+')'));
    R.forEach(r=>{ const v=D.por_tipo[r.id][t.tipo]; const n=t.idx.length*D.repeticoes, hit=Math.round(v*n); const td=el('td',undefined,'c '+cls(v)); td.appendChild(document.createTextNode(pct(v))); td.appendChild(el('small',hit+' de '+n)); td.onclick=()=>{ abrir('explorar'); st.value=k; trocarTipo(); window.scrollTo({top:0}); }; tr.appendChild(td); });
    mp.appendChild(tr); }); }

tipos.forEach((t,k)=>{ const o=el('option',nomeTipo(t.tipo)+' ('+t.idx.length+' '+(t.idx.length>1?'casos':'caso')+')'); o.value=k; st.appendChild(o); });
for(let i=1;i<=D.repeticoes;i++){ const o=el('option','Repetição '+i); o.value=i; sr.appendChild(o); }
const rotulo = c => { const g=c.gabarito; return String(g.quantidade).replace('.',',')+' '+g.unidade+' de '+g.item; };
const fmt = v => v===undefined?'—':JSON.stringify(v);
function trocarTipo(){
  const t=tipos[st.value]; sc.replaceChildren();
  t.idx.forEach(i=>{ const c=D.casos[i]; const o=el('option',c.id+' · pedido de '+rotulo(c)); o.value=i; sc.appendChild(o); });
  $('desctipo').textContent=(D.tipos[t.tipo]||['',''])[1]; mostrar();
}
function mostrar(){
  const c=D.casos[sc.value], rep=+sr.value, box=$('detalhe'); box.replaceChildren();
  box.appendChild(el('h3','Texto da solicitação (o que a pessoa escreveu)')); box.appendChild(el('pre',c.texto));
  box.appendChild(el('h3','Resposta certa × resposta de cada técnica (repetição '+rep+')'));
  const ts=Object.keys(c.saidas).sort();
  const wrap=el('div'); wrap.style.overflowX='auto'; const t=el('table',undefined,'cmp');
  const h=el('tr'); h.appendChild(el('th','Campo')); h.appendChild(el('th','Gabarito')); ts.forEach(x=>h.appendChild(el('th',x+' '+D.tecnicas[x].apelido))); t.appendChild(h);
  D.campos.forEach(f=>{ const tr=el('tr'); tr.appendChild(el('th',f)); tr.appendChild(el('td',fmt(c.gabarito[f])));
    ts.forEach(x=>{ const s=c.saidas[x][rep-1]; if(!s){ tr.appendChild(el('td','—')); return; }
      const ok=s.campos[f]===true; const v=s.parsed? fmt(s.parsed[f]) : '(JSON inválido)';
      tr.appendChild(el('td',(ok?'✓ ':'✗ ')+v,ok?'ok':'erro')); }); t.appendChild(tr); });
  const rs=el('tr'); rs.appendChild(el('th','Caso inteiro')); rs.appendChild(el('td','8 campos certos'));
  ts.forEach(x=>{ const s=c.saidas[x][rep-1]; rs.appendChild(el('td',s&&s.correto?'✓ correto':'✗ errado (oficial)',s&&s.correto?'ok':'erro')); }); t.appendChild(rs);
  wrap.appendChild(t); box.appendChild(wrap);
  const erradas=ts.filter(x=>{ const s=c.saidas[x][rep-1]; return s && !s.correto; });
  box.appendChild(el('h3','Por que errou'));
  if(!erradas.length) box.appendChild(el('p','Todas as técnicas acertaram este caso nesta repetição.','nota'));
  erradas.forEach(x=>{ const s=c.saidas[x][rep-1]; const d=el('div',undefined,'por'); d.appendChild(el('b',x+' '+D.tecnicas[x].apelido)); d.appendChild(document.createTextNode(s.porque||'Campos diferentes do gabarito.')); box.appendChild(d); });
  const dd=el('details'); dd.appendChild(el('summary','Ver a resposta bruta de cada técnica'));
  ts.forEach(x=>{ const s=c.saidas[x][rep-1]; if(!s) return; dd.appendChild(el('span',x+' '+D.tecnicas[x].apelido+(s.classe&&s.classe!=='correto'?' · classe do erro: '+s.classe:''),'rot')); dd.appendChild(el('pre',s.resposta)); });
  box.appendChild(dd);
}
// limites e glossário
D.qa.forEach(q=>{ const d=el('details',undefined,'qa'); const sm=el('summary',q[0]); const ok=/^Feito/.test(q[3]); sm.appendChild(el('span',q[3],'badge '+(q[3]==='Não feito'?'nf':ok?'ok':''))); d.appendChild(sm);
  const r=el('p',undefined,'r'); r.appendChild(el('strong','Resposta honesta: ')); r.appendChild(document.createTextNode(q[1])); d.appendChild(r);
  const m=el('p',undefined,'m'); m.appendChild(el('strong','O que mudar: ')); m.appendChild(document.createTextNode(q[2])); d.appendChild(m); $('qa').appendChild(d); });
D.prioridades.forEach(p=>{ const li=el('li'); li.appendChild(el('strong',p[0]+'. ')); li.appendChild(document.createTextNode(p[1])); $('prior').appendChild(li); });
D.glossario.forEach(([sec,itens])=>{ $('gloss').appendChild(el('h3',sec)); const dl=el('dl',undefined,'gl'); itens.forEach(([k,v])=>{ dl.appendChild(el('dt',k)); dl.appendChild(el('dd',v)); }); $('gloss').appendChild(dl); });
st.onchange=trocarTipo; sc.onchange=mostrar; sr.onchange=mostrar; trocarTipo();
window.onhashchange=()=>abrir(location.hash.slice(1));
abrir(location.hash.slice(1)||'entender');
</script></body></html>
"""


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
    pares_ok = separaveis(resumo)
    if pares_ok:
        veredito = ("Resultado oficial: " + "; ".join(f"{a} {nomes[a]} acerta mais que {b} {nomes[b]}" for a, b in pares_ok)
                    + " (intervalos de 95% que não se sobrepõem). Para os demais pares não há vencedor declarado. Veja o porquê na aba Resultados.")
    else:
        veredito = "Nenhuma técnica é declarada melhor: os intervalos de 95% se sobrepõem em todos os pares. Veja a leitura completa na aba Resultados."
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
                  "recontagem sem o defeito está marcada como pós-hoc. Ver a aba Limites e perguntas.")
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
                  "Esse ponto mede como cada prompt trata uma informação implícita, não quem entende melhor a tarefa. Ver a aba Limites e perguntas.")
    else:
        leitura = "As respostas erradas têm mais de uma causa; veja a classificação acima e o explorador de casos."
        limite = "Há erros de mais de um tipo; ver a aba Resultados."
    ficha = {"pergunta": "Qual técnica de prompt extrai melhor os dados de pedidos de compra escritos em texto livre, e quanto custa cada acerto?",
             "metodo": (f"{len(casos)} pedidos fictícios, com gabarito escrito e congelado antes de rodar. Cada uma das 4 técnicas respondeu a cada caso {reps} vezes "
                        f"({len(regs)} respostas nesta rodada). Um caso só conta como certo se os 8 campos baterem com o gabarito. Modelo: claude-haiku-5-5."),
             "limite": limite}
    return {"ficha": ficha, "qa": [list(q) for q in QA], "prioridades": [list(x) for x in PRIORIDADES], "glossario": [[a, [list(i) for i in b]] for a, b in GLOSSARIO],
            "erros": {"por_tecnica": por_tec, "rotulos": ROTULOS_CLASSE, "leitura": leitura},
            "veredito": veredito, "campos": CAMPOS, "compara": [[k, v] for k, v in COMPARA],
            "por_tipo": {t: r["acerto_tipo"] for t, r in resumo.items()},
            "tipos": {k: list(v) for k, v in TIPOS.items()}, "tecnicas": {k: TECNICAS[k] for k in resumo},
            "prompts": prompts, "resumo": tabela, "nomes": nomes, "casos": ordenados, "repeticoes": max(r["repeticoes"] for r in resumo.values()),
            "aviso": aviso, "notas": notas}


def main():
    dados = montar_dados()
    blob = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    destino = caminhos.DOCS
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "index.html").write_text(TEMPLATE.replace("__OUTRA__", "../index.html" if caminhos.VERSAO == "v2" else "v2/index.html").replace("__OUTRA_TXT__", "Ver a rodada com os dados v1 (50 casos mais simples)" if caminhos.VERSAO == "v2" else "Ver a rodada com os dados v2 (50 casos mais difíceis, sem o artefato do Ltda.)").replace("__VERSAO__", caminhos.VERSAO).replace("__DADOS__", blob), encoding="utf-8", newline="\n")
    if caminhos.VERSAO == "v1":
        linhas = ["# Preparação para entrevista: perguntas difíceis sobre o projeto", "",
                  "Gerado por `src/gerar_demo.py` a partir de `src/conteudo_demo.py`. A mesma lista aparece na aba \"Limites e perguntas\" da demo.", ""]
        for i, (q, r, m, e) in enumerate(QA, 1):
            linhas += [f"## {i}. {q}", "", f"**Estado:** {e}", "", f"**Resposta honesta:** {r}", "", f"**O que mudar:** {m}", ""]
        linhas += ["## O que eu mudaria, em ordem", ""] + [f"{i}. **{t}.** {w}" for i, (t, w) in enumerate(PRIORIDADES, 1)] + [""]
        (RAIZ / "docs" / "PREPARACAO_ENTREVISTA.md").write_text("\n".join(linhas), encoding="utf-8", newline="\n")
    print(f"{destino}/index.html gerado ({caminhos.VERSAO}): {len(dados['casos'])} casos, {len(dados['resumo'])} técnicas")


if __name__ == "__main__":
    main()
