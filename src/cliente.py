"""Cliente Anthropic com teto de gasto, retry só em erro transitório e latência.

A chave vem só de ANTHROPIC_API_KEY (variável de ambiente ou .env local). Nunca é
impressa nem gravada. O SDK é importado só na primeira chamada real, para os testes
rodarem sem API e sem o pacote.
"""
import json
import os
import time
from pathlib import Path

from custo import carregar_precos, custo_usd

RAIZ = Path(__file__).resolve().parent.parent
MODELO = "claude-haiku-5-5"
TETO_USD = 1.00
# O claude-haiku-5-5 NÃO aceita temperature/top_p/top_k (a API devolve erro 400 e o SDK 1.x
# nem expõe o argumento). Por isso não há temperatura 0: a variação é medida pelas 3 repetições.
# O raciocínio adaptativo vem ligado por padrão; fixamos o esforço em "low" para limitar o
# raciocínio oculto e o custo. Registrado em cada resultado bruto.
ESFORCO = "low"
MAX_TENTATIVAS = 3          # 1 chamada + 2 retries; depois disso, para e relata
ESPERA_S = (2.0, 5.0)
# estimativa conservadora para a reserva: 1 token a cada 2 caracteres (PT-BR tem mais tokens por caractere)
CARACTERES_POR_TOKEN_RESERVA = 2


class TetoExcedido(RuntimeError):
    pass


def carregar_env(caminho=RAIZ / ".env"):
    """Lê .env simples (CHAVE=valor) para os.environ, sem sobrescrever o que já existe."""
    if not Path(caminho).exists():
        return
    for linha in Path(caminho).read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            k, v = linha.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class ControleCusto:
    """Livro-caixa persistente do gasto. Reserva o custo máximo ANTES de cada chamada."""

    def __init__(self, arquivo=RAIZ / "logs" / "gasto.json", teto=TETO_USD):
        self.arquivo, self.teto = Path(arquivo), teto
        self.gasto = 0.0
        if self.arquivo.exists():
            self.gasto = json.loads(self.arquivo.read_text(encoding="utf-8")).get("gasto_usd", 0.0)

    def reservar(self, custo_maximo: float):
        if self.gasto + custo_maximo > self.teto:
            self._log_erro(f"teto excedido: gasto={self.gasto:.6f} + reserva={custo_maximo:.6f} > teto={self.teto:.2f}")
            raise TetoExcedido(f"Chamada bloqueada: gasto {self.gasto:.4f} + reserva {custo_maximo:.4f} passaria de US$ {self.teto:.2f}")

    def registrar(self, custo_real: float):
        self.gasto += custo_real
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        self.arquivo.write_text(json.dumps({"gasto_usd": round(self.gasto, 8), "teto_usd": self.teto}) + "\n", encoding="utf-8")

    def _log_erro(self, msg):
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        with open(self.arquivo.parent / "erros.log", "a", encoding="utf-8") as f:
            f.write(msg + "\n")


def _transitorio(exc) -> bool:
    nome = type(exc).__name__
    if nome in {"APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError", "OverloadedError"}:
        return True
    return getattr(exc, "status_code", None) in {408, 409, 429, 500, 502, 503, 504, 529}


class ClienteAnthropic:
    def __init__(self, controle: ControleCusto, precos=None, enviar=None, dormir=time.sleep):
        self.controle = controle
        self.precos = precos or carregar_precos()
        self._enviar = enviar      # injetável nos testes
        self._dormir = dormir
        self._sdk = None

    def _enviar_real(self, system, user, max_tokens):
        if self._sdk is None:
            carregar_env()
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError("ANTHROPIC_API_KEY ausente (use .env local ou variável de ambiente)")
            import anthropic  # importado aqui para os testes não exigirem o SDK
            self._sdk = anthropic.Anthropic(max_retries=0)  # retry é controlado por nós
        kwargs = dict(model=MODELO, max_tokens=max_tokens,
                      extra_body={"output_config": {"effort": ESFORCO}},
                      messages=[{"role": "user", "content": user}])
        if system:
            kwargs["system"] = system
        r = self._sdk.messages.create(**kwargs)
        texto = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return {"texto": texto, "tokens_entrada": r.usage.input_tokens, "tokens_saida": r.usage.output_tokens,
                "stop_reason": getattr(r, "stop_reason", None)}

    def chamar(self, system: str, user: str, max_tokens: int) -> dict:
        est_in = (len(system) + len(user)) // CARACTERES_POR_TOKEN_RESERVA + 1
        self.controle.reservar(custo_usd(est_in, max_tokens, self.precos))
        enviar = self._enviar or self._enviar_real
        for tentativa in range(1, MAX_TENTATIVAS + 1):
            t0 = time.perf_counter()
            try:
                r = enviar(system, user, max_tokens)
            except Exception as exc:  # noqa: BLE001
                if not _transitorio(exc) or tentativa == MAX_TENTATIVAS:
                    self.controle._log_erro(f"falha na tentativa {tentativa}: {type(exc).__name__}")
                    raise
                self._dormir(ESPERA_S[min(tentativa - 1, len(ESPERA_S) - 1)])
                continue
            latencia = time.perf_counter() - t0
            custo = custo_usd(r["tokens_entrada"], r["tokens_saida"], self.precos)
            self.controle.registrar(custo)
            return {**r, "custo_usd": custo, "latencia_s": latencia, "tentativas": tentativa}
