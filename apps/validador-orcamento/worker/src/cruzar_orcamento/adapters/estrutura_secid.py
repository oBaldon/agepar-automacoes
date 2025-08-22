# apps/validador-orcamento/worker/src/cruzar_orcamento/adapters/estrutura_secid.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple
import math

import pandas as pd

from ..models import EstruturaDict, CompEstrutura, ChildSpec
from ..utils.utils_code import norm_code_canonical as _norm_code


def _norm_text(x: object) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):  # type: ignore[arg-type]
        return ""
    return str(x).strip().lower()


def _to_float(x: object) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, str):
            s = x.strip()
            if s == "":
                return None
            s = s.replace(".", "") if s.count(".") > 1 and s.count(",") == 1 else s
            s = s.replace(",", ".")
            v = float(s)
        else:
            v = float(x)
        if math.isnan(v):
            return None
        return v
    except Exception:
        return None


def _find_header(df: pd.DataFrame) -> Tuple[int, Dict[str, int]]:
    """
    Detecta a linha de cabeçalho e índices:
    - tipo, código, descrição, unidade, coeficiente
    """
    n = len(df)
    for r in range(min(50, n)):
        row = [_norm_text(v) for v in df.iloc[r].tolist()]
        joined = " ".join(row)
        if ("tipo" in joined) and ("descr" in joined) and ("cód" in joined or "cod" in joined):
            cols = {"tipo": -1, "codigo": -1, "descricao": -1, "unidade": -1, "coeficiente": -1}
            for c, val in enumerate(row):
                if cols["tipo"] < 0 and "tipo" in val:
                    cols["tipo"] = c
                elif cols["codigo"] < 0 and ("cód" in val or "cod" in val):
                    cols["codigo"] = c
                elif cols["descricao"] < 0 and "descr" in val:
                    cols["descricao"] = c
                elif cols["unidade"] < 0 and ("unid" in val or "und" in val):
                    cols["unidade"] = c
                elif cols["coeficiente"] < 0 and ("coef" in val or "quant" in val):
                    cols["coeficiente"] = c
            return r, cols
    raise ValueError("Cabeçalho da planilha SECID (estrutura) não encontrado.")


def load_estrutura_secid(path: Path | str) -> EstruturaDict:
    """
    Monta:
      { codigo_canon: CompEstrutura(codigo, descricao, unidade, filhos=[ChildSpec(...)]) }

    Regras:
      - Linha com TIPO vazio abre um novo pai.
      - Linhas com TIPO em {"composicao","composição","insumo"} viram filhos do pai corrente.
    """
    path = Path(path)
    xls = pd.ExcelFile(path)
    df = pd.read_excel(xls, sheet_name=xls.sheet_names[0], header=None)

    row0, cols = _find_header(df)

    # auto-skip de uma possível linha de custos logo abaixo do cabeçalho
    start = row0 + 1
    if row0 + 1 < len(df):
        sub = " ".join(_norm_text(v) for v in df.iloc[row0 + 1].tolist())
        if any(tok in sub for tok in ("material", "mão", "mao", "total")):
            start = row0 + 2

    out: EstruturaDict = {}
    current: Optional[CompEstrutura] = None

    def _flush_current() -> None:
        nonlocal current
        if current is None:
            return
        out[_norm_code(current["codigo"])] = current
        current = None

    for i in range(start, len(df)):
        row = df.iloc[i]

        tipo = _norm_text(row.iloc[cols["tipo"]]) if cols["tipo"] >= 0 else ""
        codigo_raw = row.iloc[cols["codigo"]] if cols["codigo"] >= 0 else None
        desc_raw = row.iloc[cols["descricao"]] if cols["descricao"] >= 0 else None
        uni_raw = row.iloc[cols["unidade"]] if cols["unidade"] >= 0 else None
        coef_raw = row.iloc[cols["coeficiente"]] if cols["coeficiente"] >= 0 else None

        # código em branco/NaN → ignora a linha por completo
        if codigo_raw is None or pd.isna(codigo_raw):
            # se for uma linha completamente vazia, só segue
            if not tipo and (desc_raw is None or pd.isna(desc_raw)):
                continue
            # sem código não dá para indexar nada
            continue

        codigo = str(codigo_raw).strip()
        if not codigo or codigo.lower() == "nan":
            continue

        descricao = "" if desc_raw is None or pd.isna(desc_raw) else str(desc_raw).strip()
        unidade = None if uni_raw is None or pd.isna(uni_raw) else (str(uni_raw).strip() or None)
        coef = _to_float(coef_raw)

        # pai: tem código e TIPO vazio
        if not tipo:
            _flush_current()
            current = CompEstrutura(
                codigo=codigo,
                descricao=descricao,
                unidade=unidade,
                filhos=[],            # type: ignore[list-item]
                banco="SECID",
            )
            continue

        # filho ligado ao pai atual
        if current is not None and tipo in {"insumo", "composicao", "composição"}:
            child = ChildSpec(
                codigo=codigo,
                descricao=descricao,
                unidade=unidade,
                coeficiente=coef,
            )
            current["filhos"].append(child)  # type: ignore[index]

    _flush_current()
    return out
