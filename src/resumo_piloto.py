"""Resumo do piloto: uma linha por chamada, sem expor chave (ela nunca é gravada).

  python src/resumo_piloto.py [pasta]   (padrão: resultados/brutos/piloto)
"""
import json
import sys
from pathlib import Path

pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "resultados" / "brutos" / "piloto"
regs = [json.loads(a.read_text(encoding="utf-8")) for a in sorted(pasta.glob("*.json"))]
print(f"{'tec':3} {'caso':4} {'ok':3} {'json':4} {'stop':10} {'t_in':>5} {'t_out':>5} {'custo_usd':>10} {'lat_s':>6} tent")
for r in regs:
    a = r["avaliacao"]
    print(f"{r['tecnica']:3} {r['caso']:4} {'sim' if a['caso_correto'] else 'não':3} {'sim' if a['json_valido'] else 'não':4} "
          f"{str(r.get('stop_reason')):10} {r['tokens_entrada']:>5} {r['tokens_saida']:>5} {r['custo_usd']:>10.6f} {r['latencia_s']:>6.2f} {r['tentativas']}")
print(f"\n{len(regs)} registros | corretos: {sum(r['avaliacao']['caso_correto'] for r in regs)} | custo total: US$ {sum(r['custo_usd'] for r in regs):.6f}")
for r in regs:
    if not r["avaliacao"]["caso_correto"]:
        erros = [c for c, ok in r["avaliacao"]["campos"].items() if not ok]
        print(f"\n[{r['tecnica']} {r['caso']}] campos errados: {erros}\n  resposta: {r['resposta'][:300]!r}")
