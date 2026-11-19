"""Validação do JSON extraído e regra de acerto. Regras definidas ANTES de medir.

Extração do JSON da resposta:
- T1, T2, T4: a resposta inteira deve ser um objeto JSON. Única tolerância: cerca
  de markdown ```json ... ``` ao redor é removida.
- T3: só o conteúdo de <json>...</json> é lido (raciocínio é ignorado).

Acerto por campo (normalização): texto sem acento, minúsculo, espaços colapsados;
números exatos (5 == 5.0; string "5" NÃO vale); datas ISO; null só igual a null.
Acerto por caso: JSON válido + schema pydantic válido (extra="forbid") + os 8 campos
iguais ao gabarito.
"""
import json
import re
import unicodedata
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, StrictFloat, StrictInt, StrictStr, ValidationError, field_validator

CAMPOS = ["solicitante_area", "item", "quantidade", "unidade",
          "prazo_entrega", "valor_unitario", "moeda", "fornecedor"]
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Solicitacao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    solicitante_area: Optional[StrictStr]
    item: StrictStr
    quantidade: StrictInt | StrictFloat
    unidade: Literal["un", "kg", "m", "l", "cx"]
    prazo_entrega: Optional[StrictStr]
    valor_unitario: Optional[StrictInt | StrictFloat]
    moeda: Optional[Literal["BRL", "USD", "EUR"]]
    fornecedor: Optional[StrictStr]

    @field_validator("prazo_entrega")
    @classmethod
    def _data_iso(cls, v):
        if v is not None and not _ISO.match(v):
            raise ValueError("prazo_entrega deve ser AAAA-MM-DD ou null")
        return v


def extrair_json_texto(resposta: str, tecnica_id: str) -> Optional[str]:
    """Devolve o texto que deve conter o JSON, ou None se não achou."""
    if tecnica_id == "T3":
        m = re.search(r"<json>(.*?)</json>", resposta, re.DOTALL)
        if not m:
            return None
        resposta = m.group(1)
    s = resposta.strip()
    m = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", s, re.DOTALL)
    return m.group(1) if m else s


def parse(resposta: str, tecnica_id: str):
    """-> (dict ou None, json_valido: bool)"""
    texto = extrair_json_texto(resposta, tecnica_id)
    if texto is None:
        return None, False
    try:
        obj = json.loads(texto)
    except (json.JSONDecodeError, ValueError):
        return None, False
    return (obj, True) if isinstance(obj, dict) else (None, False)


def norm_texto(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def _eh_numero(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def campo_igual(previsto, esperado) -> bool:
    if esperado is None or previsto is None:
        return esperado is None and previsto is None
    if _eh_numero(esperado):
        return _eh_numero(previsto) and float(previsto) == float(esperado)
    if isinstance(esperado, str):
        return isinstance(previsto, str) and norm_texto(previsto) == norm_texto(esperado)
    return False


def avaliar(resposta: str, gabarito: dict, tecnica_id: str) -> dict:
    """Pontua uma resposta contra o gabarito de um caso."""
    obj, json_valido = parse(resposta, tecnica_id)
    campos = {c: False for c in CAMPOS}
    schema_valido = False
    if json_valido:
        try:
            Solicitacao.model_validate(obj)
            schema_valido = True
        except ValidationError:
            pass
        for c in CAMPOS:
            campos[c] = c in obj and campo_igual(obj[c], gabarito[c])
    return {"json_valido": json_valido, "schema_valido": schema_valido, "campos": campos,
            "caso_correto": json_valido and schema_valido and all(campos.values())}
