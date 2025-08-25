# apps/validador-orcamento/worker/src/cruzar_orcamento/adapters/secid.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple
import math

import pandas as pd

from ..models import Item, CanonDict
from ..utils.utils_code import norm_code_canonical as _norm_code


def _norm_text(x: object) -> str:
    """Lower + strip, tolerante a NaN."""
    if x is None or (isinstance(x, float) and math.isnan(x)):  # type: ignore
        return ""
    return str(x).strip().lower()


def _to_float(x: object) -> Optional[float]:
    """Converte valores para float; retorna None se vazio/NaN/inválido.
    Regras:
      - strings vazias -> None
      - se tiver ponto e vírgula, assume que o ÚLTIMO separador é o decimal
        (o outro vira separador de milhar e é removido)
      - só vírgula -> trata como decimal (pt-BR)
      - só ponto -> trata como decimal (en-US)
    """
    try:
        if x is None:
            return None

        if isinstance(x, str):
            s = x.strip()
            if not s:
                return None

            # negativos entre parênteses: (123,45) -> -123,45
            if s.startswith("(") and s.endswith(")"):
                s = "-" + s[1:-1].strip()

            # remover espaços/nbsp de milhar
            s = s.replace("\u00A0", "").replace(" ", "")

            if "," in s and "." in s:
                # o último separador é o decimal
                if s.rfind(",") > s.rfind("."):
                    # vírgula como decimal -> remove pontos (milhar) e troca vírgula por ponto
                    s = s.replace(".", "").replace(",", ".")
                else:
                    # ponto como decimal -> remove vírgulas (milhar)
                    s = s.replace(",", "")
            elif "," in s:
                # apenas vírgula -> decimal vírgula
                s = s.replace(".", "")  # guarda-chuva p/ casos "1.234,56"
                s = s.replace(",", ".")
            else:
                # apenas ponto ou nenhum separador -> deixa como está
                pass

            v = float(s)
            if math.isnan(v):
                return None
            return v

        # numérico já parseável
        v = float(x)
        if math.isnan(v):
            return None
        return v

    except Exception:
        return None


def _find_header(df: pd.DataFrame) -> Tuple[int, Dict[str, int], Dict[str, int]]:
    """
    Detecta a linha de cabeçalho e mapeia colunas.
    Esperado no cabeçalho (mesma linha): 'tipo', 'códig', 'descr', 'unid', 'coef'.
    Na linha seguinte, subcabeçalhos de custo: 'material', 'mão'/'mao', 'total'.
    Retorna: (row_header, cols, cost_cols)
    """
    n = len(df)
    for r in range(min(50, n - 1)):
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
                elif cols["unidade"] < 0 and "unid" in val:
                    cols["unidade"] = c
                elif cols["coeficiente"] < 0 and "coef" in val:
                    cols["coeficiente"] = c

            # subcabeçalho de custos na linha seguinte
            sub = [_norm_text(v) for v in df.iloc[r + 1].tolist()]
            cost = {"material": -1, "mao": -1, "total": -1}
            for c, v in enumerate(sub):
                if cost["material"] < 0 and "material" in v:
                    cost["material"] = c
                elif cost["mao"] < 0 and ("mão" in v or "mao" in v or "mdo" in v or "mão-de-obra" in v):
                    cost["mao"] = c
                elif cost["total"] < 0 and "total" in v:
                    cost["total"] = c

            if cols["codigo"] >= 0 and cols["descricao"] >= 0:
                return r, cols, cost

    raise ValueError("Cabeçalho da planilha SECID não encontrado.")


def load_secid_precos(path: Path | str) -> CanonDict:
    """
    Lê planilha da SECID (Edificações) e retorna um CanonDict:
      { codigo_canon: Item(codigo, descricao, valor_unit, unidade, banco='SECID') }

    Regras:
      - Linhas com TIPO vazio e CÓDIGO presente são tratadas como “cabeçalho de composição”
        e delas extraímos o preço unitário da composição (TOTAL ou MATERIAL+MÃO).
      - Linhas de insumos/filhos são ignoradas para efeito de preço unitário da composição.
    """
    path = Path(path)
    xls = pd.ExcelFile(path)
    df = pd.read_excel(xls, sheet_name=xls.sheet_names[0], header=None)

    row0, cols, cost = _find_header(df)
    start = row0 + 2  # pula linha de subcabeçalho

    out: CanonDict = {}
    fonte = "SECID/Edificações (desonerado)"

    for i in range(start, len(df)):
        row = df.iloc[i]

        tipo = _norm_text(row.iloc[cols["tipo"]]) if cols["tipo"] >= 0 else ""
        codigo_raw = row.iloc[cols["codigo"]] if cols["codigo"] >= 0 else None
        desc_raw = row.iloc[cols["descricao"]] if cols["descricao"] >= 0 else None
        uni_raw = row.iloc[cols["unidade"]] if cols["unidade"] >= 0 else None

        # códigos vazios/NaN são descartados
        if codigo_raw is None or pd.isna(codigo_raw):
            continue

        codigo = str(codigo_raw).strip()
        if not codigo:
            continue

        descricao = "" if desc_raw is None or pd.isna(desc_raw) else str(desc_raw).strip()
        unidade = None if uni_raw is None or pd.isna(uni_raw) else str(uni_raw).strip() or None

        # “cabeçalho de composição”: TIPO vazio (NaN/"") e há código
        if not tipo:
            mat = _to_float(row.iloc[cost["material"]]) if cost["material"] >= 0 else None
            mao = _to_float(row.iloc[cost["mao"]]) if cost["mao"] >= 0 else None
            tot = _to_float(row.iloc[cost["total"]]) if cost["total"] >= 0 else None

            if tot is None:
                # fallback: soma Material+Mão quando possível
                tot = (mat or 0.0) + (mao or 0.0) if (mat is not None or mao is not None) else None

            if tot is None:
                # composição sem preço total legível
                continue

            code_canon = _norm_code(codigo)
            out[code_canon] = Item(
                codigo=codigo,
                descricao=descricao,
                valor_unit=tot,
                unidade=unidade,
                banco="SECID",
                fonte=fonte,
            )

    return out
