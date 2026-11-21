"""Experimentos E3, E4, E5 e a medição do P4: variantes, execução e gravação das respostas brutas.

Teto de gasto das rodadas novas: US$ 0,60 (ControleBiblioteca). O repositório já tinha gasto US$ 0,248969 de um
teto de US$ 1,00; o controle também garante que o total nunca passe de US$ 1,00. O custo máximo é reservado ANTES
de cada chamada e, se a próxima passaria do teto, a rodada para com erro registrado em logs/erros.log.

Cada resposta bruta é uma linha em resultados/biblioteca/brutos/<exp>_<variante>.jsonl (uma linha por caso e
repetição, com todas as etapas, tokens, custo, latência e a avaliação). A execução é retomável: linha que já
existe é pulada. Para no primeiro erro que sobrar depois dos retries do cliente (no máximo 3 tentativas).
"""
import json
import random
from pathlib import Path

import avaliadores
import prompts_biblioteca as pb
from cliente import ESFORCO, MODELO, ClienteAnthropic, ControleCusto, TetoExcedido
from custo import custo_usd  # noqa: F401  (reexportado para os relatórios)

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados" / "biblioteca"
RESULTADOS = RAIZ / "resultados" / "biblioteca"
BRUTOS = RESULTADOS / "brutos"
PILOTO = RESULTADOS / "piloto"

GASTO_ANTERIOR_USD = 0.248969   # gasto das rodadas v1, v2 e da iteração (README, seção 7.4)
TETO_TOTAL_USD = 1.00
TETO_RODADAS_USD = 0.60
REPETICOES = 3
CASOS_PILOTO = 5
CUSTO_P1_ESTIMADO = 0.000145    # custo médio por chamada do T4 v2 medido na iteração (resultados/extracao/v2/iteracao.json)

# folga para o raciocínio oculto (conta como saída); o teto continua valendo
MAX_TOKENS = {("P1", "system_prompt"): 2000, ("P2", "zero_shot"): 1500, ("P2", "few_shot"): 1500,
              ("P3", "encadeado"): 2000, ("P3", "unico"): 2000, ("P4", "saida_estruturada"): 2000,
              ("P5", "direto"): 2000, ("P5", "chain_of_thought"): 3000}

# (experimento, variante) -> dados, passos (id do prompt, técnica, versão) e se o P5 usa <json>
VARIANTES = {
    ("E3", "zero_shot"): {"dados": "p2", "passos": [("P2", "zero_shot", "v1")]},
    ("E3", "few_shot"): {"dados": "p2", "passos": [("P2", "few_shot", "v1")]},
    ("E4", "encadeado"): {"dados": "p3", "passos": [("P1", "system_prompt", "v2"), ("P3", "encadeado", "v1")]},
    ("E4", "unico"): {"dados": "p3", "passos": [("P3", "unico", "v1")]},
    # E6: mesmo fluxo do E4 encadeado, trocando só o e-mail (P3 v1 -> P3 v2). O v1 é o E4/encadeado já medido.
    ("E6", "encadeado_v2"): {"dados": "p3", "passos": [("P1", "system_prompt", "v2"), ("P3", "encadeado", "v2")]},
    ("P4", "saida_estruturada"): {"dados": "p4", "passos": [("P4", "saida_estruturada", "v1")]},
    ("E5", "direto"): {"dados": "p5", "passos": [("P5", "direto", "v1")]},
    ("E5", "cot"): {"dados": "p5", "passos": [("P5", "chain_of_thought", "v1")], "cot": True},
}
ORDEM = [("E3", "zero_shot"), ("E3", "few_shot"), ("E4", "encadeado"), ("E4", "unico"),
         ("P4", "saida_estruturada"), ("E5", "direto"), ("E5", "cot"), ("E6", "encadeado_v2")]


class ControleBiblioteca(ControleCusto):
    """Livro-caixa das rodadas novas: teto de US$ 0,60 e, ao mesmo tempo, nunca passar de US$ 1,00 no total."""

    def __init__(self, arquivo=RAIZ / "logs" / "gasto_biblioteca.json", teto=TETO_RODADAS_USD,
                 anterior=GASTO_ANTERIOR_USD, teto_total=TETO_TOTAL_USD):
        super().__init__(arquivo=arquivo, teto=teto)
        self.anterior, self.teto_total = anterior, teto_total

    def reservar(self, custo_maximo: float):
        if self.anterior + self.gasto + custo_maximo > self.teto_total:
            self._log_erro(f"teto total excedido: anterior={self.anterior:.6f} + novo={self.gasto:.6f} + reserva={custo_maximo:.6f} > {self.teto_total:.2f}")
            raise TetoExcedido(f"Chamada bloqueada: o total do repositório passaria de US$ {self.teto_total:.2f}")
        super().reservar(custo_maximo)


def carregar_dados(nome, dados=DADOS):
    casos = json.loads((dados / nome / "casos_teste.json").read_text(encoding="utf-8"))
    gab = json.loads((dados / nome / "gabarito.json").read_text(encoding="utf-8"))
    return sorted(casos, key=lambda c: c["id"]), gab


def executar_caso(cliente, cfg, caso, gab_caso, entrada_inicial=None, passos=None):
    """Roda os passos de uma variante em um caso. Cada passo recebe a resposta do anterior (encadeamento)."""
    entrada = caso["texto"] if entrada_inicial is None else entrada_inicial
    etapas, resposta = [], ""
    for pid, tec, ver in (passos or cfg["passos"]):
        prompt = pb.carregar(pid, tec, ver)
        system, user = pb.montar(prompt, entrada)
        r = cliente.chamar(system, user, MAX_TOKENS[(pid, tec)])
        etapas.append({"prompt": pid, "tecnica": tec, "versao": ver, "hash12": prompt["hash12"], "resposta": r["texto"],
                       "tokens_entrada": r["tokens_entrada"], "tokens_saida": r["tokens_saida"], "custo_usd": r["custo_usd"],
                       "latencia_s": r["latencia_s"], "tentativas": r["tentativas"], "stop_reason": r.get("stop_reason")})
        resposta = r["texto"]
        entrada = resposta
    aval = avaliadores.avaliar(cfg["dados"], resposta, gab_caso, caso["texto"], cot=cfg.get("cot", False))
    return {"caso": caso["id"], "tipo": caso["tipo"], "resposta": resposta, "etapas": etapas,
            "custo_usd": sum(e["custo_usd"] for e in etapas), "latencia_s": sum(e["latencia_s"] for e in etapas),
            "avaliacao": aval}


def _chaves_existentes(arq):
    if not arq.exists():
        return set()
    return {(j["caso"], j["repeticao"]) for j in map(json.loads, filter(None, arq.read_text(encoding="utf-8").splitlines()))}


def executar_variante(cliente, exp, variante, pasta=BRUTOS, dados=DADOS, reps=REPETICOES, limite_casos=None):
    """-> (feitas, novas, parou_por). parou_por é None se terminou."""
    cfg = VARIANTES[(exp, variante)]
    casos, gab = carregar_dados(cfg["dados"], dados)
    if limite_casos:
        casos = casos[:limite_casos]
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / f"{exp}_{variante}.jsonl"
    existentes = _chaves_existentes(arq)
    feitas = novas = 0
    for caso in casos:
        for rep in range(1, reps + 1):
            if (caso["id"], rep) in existentes:
                feitas += 1
                continue
            try:
                reg = executar_caso(cliente, cfg, caso, gab[caso["id"]])
            except Exception as exc:  # noqa: BLE001  (teto, falha da API depois dos retries)
                return feitas, novas, f"{type(exc).__name__}: {exc}"
            reg.update({"experimento": exp, "variante": variante, "repeticao": rep, "modelo": MODELO, "esforco": ESFORCO})
            with open(arq, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(reg, ensure_ascii=False) + "\n")
            novas += 1
            print(f"[{exp} {variante} {caso['id']} r{rep}] ok={reg['avaliacao']['caso_correto']} custo=US$ {reg['custo_usd']:.6f} gasto_novo={cliente.controle.gasto:.6f}", flush=True)
    return feitas, novas, None


# ---------------------------------------------------------------- piloto
def casos_do_piloto(casos):
    ids = sorted(random.Random(42).sample([c["id"] for c in casos], CASOS_PILOTO))
    return [c for c in casos if c["id"] in ids]


def executar_piloto(cliente, pasta=PILOTO, dados=DADOS):
    """5 chamadas por prompt novo (P2 few-shot, P3 encadeado, P4, P5 com raciocínio), 1 repetição.

    No P3 a entrada é a extração do gabarito (o piloto não gasta uma chamada do P1); o fluxo P1 -> P3 é
    exercitado pelos testes sem API e só roda de verdade na rodada completa."""
    pasta.mkdir(parents=True, exist_ok=True)
    planos = [("P2", ("E3", "few_shot")), ("P3", ("E4", "encadeado")), ("P4", ("P4", "saida_estruturada")), ("P5", ("E5", "cot"))]
    saida, linhas = {}, []
    for rotulo, chave in planos:
        cfg = VARIANTES[chave]
        casos, gab = carregar_dados(cfg["dados"], dados)
        regs = []
        for caso in casos_do_piloto(casos):
            entrada, passos = None, None
            if rotulo == "P3":
                entrada = json.dumps(gab[caso["id"]]["extracao"], ensure_ascii=False)
                passos = [("P3", "encadeado", "v1")]
            try:
                reg = executar_caso(cliente, cfg, caso, gab[caso["id"]], entrada_inicial=entrada, passos=passos)
            except Exception as exc:  # noqa: BLE001
                saida[rotulo] = {"erro": f"{type(exc).__name__}: {exc}"}
                regs = None
                break
            reg.update({"prompt_piloto": rotulo, "repeticao": 1, "modelo": MODELO, "esforco": ESFORCO})
            regs.append(reg)
            linhas.append(reg)
            print(f"[piloto {rotulo} {caso['id']}] ok={reg['avaliacao']['caso_correto']} custo=US$ {reg['custo_usd']:.6f}", flush=True)
        if regs is None:
            break
        n = len(regs)
        saida[rotulo] = {"chamadas": n, "acertos": sum(r["avaliacao"]["caso_correto"] for r in regs),
                         "custo_total_usd": sum(r["custo_usd"] for r in regs), "custo_medio_usd": sum(r["custo_usd"] for r in regs) / n,
                         "latencia_media_s": sum(r["latencia_s"] for r in regs) / n}
    (pasta / "piloto.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in linhas), encoding="utf-8", newline="\n")
    saida["projecao_rodada_completa_usd"] = projetar(saida) if all("custo_medio_usd" in v for v in saida.values() if isinstance(v, dict)) and len(saida) == 4 else None
    saida["gasto_piloto_usd"] = sum(v.get("custo_total_usd", 0.0) for v in saida.values() if isinstance(v, dict))
    (pasta / "piloto.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return saida


def executar_piloto_p3v2(cliente, pasta=PILOTO, dados=DADOS, reps=REPETICOES):
    """5 chamadas do P3 v2 (1 repetição), com a extração do gabarito como entrada (como no piloto do P3 v1).

    Grava piloto_p3v2.jsonl e piloto_p3v2.json sem mexer no piloto original. A projeção da rodada do E6 usa o custo
    médio medido aqui mais o custo do P1 (CUSTO_P1_ESTIMADO)."""
    pasta.mkdir(parents=True, exist_ok=True)
    cfg = VARIANTES[("E6", "encadeado_v2")]
    casos, gab = carregar_dados(cfg["dados"], dados)
    regs = []
    erro = None
    for caso in casos_do_piloto(casos):
        entrada = json.dumps(gab[caso["id"]]["extracao"], ensure_ascii=False)
        try:
            reg = executar_caso(cliente, cfg, caso, gab[caso["id"]], entrada_inicial=entrada, passos=[("P3", "encadeado", "v2")])
        except Exception as exc:  # noqa: BLE001
            erro = f"{type(exc).__name__}: {exc}"
            break
        reg.update({"prompt_piloto": "P3v2", "repeticao": 1, "modelo": MODELO, "esforco": ESFORCO})
        regs.append(reg)
        print(f"[piloto P3 v2 {caso['id']}] ok={reg['avaliacao']['caso_correto']} custo=US$ {reg['custo_usd']:.6f}", flush=True)
    n = len(regs)
    saida = {"chamadas": n, "acertos": sum(r["avaliacao"]["caso_correto"] for r in regs), "erro": erro,
             "custo_total_usd": sum(r["custo_usd"] for r in regs),
             "custo_medio_usd": (sum(r["custo_usd"] for r in regs) / n) if n else None,
             "latencia_media_s": (sum(r["latencia_s"] for r in regs) / n) if n else None}
    saida["projecao_rodada_completa_usd"] = (20 * reps * (saida["custo_medio_usd"] + CUSTO_P1_ESTIMADO)) if (n == CASOS_PILOTO and not erro) else None
    saida["gasto_piloto_usd"] = saida["custo_total_usd"]
    (pasta / "piloto_p3v2.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in regs), encoding="utf-8", newline="\n")
    (pasta / "piloto_p3v2.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return saida


def projetar(piloto, reps=REPETICOES):
    """Estimativa (não medida) do custo da rodada completa a partir do custo médio por chamada do piloto.

    Usa o custo do prompt da biblioteca para as duas variantes de cada experimento (os controles tendem a ser
    iguais ou mais baratos, então é um valor conservador) e o custo do T4 v2 para a primeira etapa do fluxo do E4."""
    n = 20 * reps
    p2, p3, p4, p5 = (piloto[k]["custo_medio_usd"] for k in ("P2", "P3", "P4", "P5"))
    return n * 2 * p2 + n * (p3 + CUSTO_P1_ESTIMADO) + n * p3 + n * p4 + n * 2 * p5
