# src/cruzar_orcamento/processor.py
from __future__ import annotations

from typing import TypedDict, List, Tuple, Dict, Optional
from ..models import Item, CanonDict
from ..utils.utils_text import norm_text


class CruzadoRow(TypedDict):
    codigo: str
    a_banco: Optional[str]
    a_desc: str
    a_valor: float
    b_desc: Optional[str]
    b_valor: Optional[float]
    match: bool


class DivergenciaRow(TypedDict):
    codigo: str
    motivos: List[str]
    dif_abs: Optional[float]
    dif_rel: Optional[float]
    dir: str  # "MAIOR" | "MENOR" | "IGUAL" | ""


def filtrar_orcamento_por_banco(orc: CanonDict, banco: Optional[str]) -> CanonDict:
    """Retorna apenas itens do orçamento cujo item['banco'] == banco (case-insensitive).
    Se banco=None, retorna o dict original.
    """
    if not banco:
        return orc
    alvo = banco.casefold().strip()
    return {
        cod: it
        for cod, it in orc.items()
        if it.get("banco") and it["banco"].casefold().strip() == alvo
    }


def _dir(a_val: Optional[float], b_val: Optional[float]) -> str:
    """Direção da divergência (referência = banco externo)."""
    if a_val is None or b_val is None:
        return ""
    if a_val > b_val:
        return "MAIOR"   # orçamento > referência
    if a_val < b_val:
        return "MENOR"   # orçamento < referência
    return "IGUAL"


def cruzar(
    orcamento: CanonDict,
    referencia: CanonDict,
    *,
    banco: Optional[str] = None,
    tol_rel: float = 0.02,              # 2% por padrão
    comparar_descricao: bool = True,
) -> Tuple[List[CruzadoRow], List[DivergenciaRow]]:
    """Cruza dicionário de ORÇAMENTO (A) com dicionário de referência (B) (ex.: SUDECAP/SINAPI).

    - Se `banco` for informado, o orçamento é filtrado antes do match.
    - Divergência de valor: |A-B|/B > tol_rel (quando B > 0).
    - Divergência de descrição: comparação normalizada (casefold+sem acento); pode desligar com `comparar_descricao=False`.
    """
    A = filtrar_orcamento_por_banco(orcamento, banco)
    cruzado: List[CruzadoRow] = []
    diverg: List[DivergenciaRow] = []

    for codigo, a in A.items():
        codigo_base = a["codigo"]
        b = referencia.get(codigo_base)
        match = b is not None

        b_desc = b["descricao"] if b else None
        b_val  = b["valor_unit"] if b else None
        a_val  = a["valor_unit"]

        cruzado.append(CruzadoRow(
            codigo=codigo_base,
            a_banco=a.get("banco"),
            a_desc=a["descricao"],
            a_valor=a_val,
            b_desc=b_desc,
            b_valor=b_val,
            match=match,
        ))

        motivos: List[str] = []
        dif_abs: Optional[float] = None
        dif_rel: Optional[float] = None
        direcao: str = ""

        if not match:
            motivos.append("CODIGO_NAO_ENCONTRADO")
            # direção permanece "", pois não há valor de referência
        else:
            # valor
            if b_val is None or b_val == 0:
                # referência zerada/nula: só marcamos se forem diferentes
                if a_val != (b_val or 0):
                    motivos.append("VALOR_BASE_ZERO_OU_NULO")
                    direcao = _dir(a_val, b_val or 0.0)
            else:
                dif_abs = abs(a_val - b_val)
                dif_rel = dif_abs / b_val
                if dif_rel > tol_rel:
                    motivos.append("VALOR_DIVERGENTE")
                    direcao = _dir(a_val, b_val)

            # descrição
            if comparar_descricao:
                if norm_text(a["descricao"]) != norm_text(b_desc or ""):
                    motivos.append("DESCRICAO_DIVERGENTE")

        if motivos:
            diverg.append(DivergenciaRow(
                codigo=codigo_base,
                motivos=motivos,
                dif_abs=dif_abs,
                dif_rel=dif_rel,
                dir=direcao,
            ))

    return cruzado, diverg
