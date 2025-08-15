# src/cruzar_orcamento/adapters/orcamento.py
from __future__ import annotations

import logging
from typing import Iterable
import unicodedata
import pandas as pd

from ..models import Item, CanonDict
from ..utils.utils_text import norm_code

logger = logging.getLogger(__name__)

# ---------- Heurísticas / normalização ----------

def _strip_accents(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()

def _norm(s: str) -> str:
    if not isinstance(s, str):
        s = "" if pd.isna(s) else str(s)
    s = _strip_accents(s).lower().strip()
    return s

def _looks_like_composicoes(name: str) -> bool:
    n = _norm(name)
    return "compos" in n  # "Composições", "Composicoes", etc.

def _find_header_row(df_raw: pd.DataFrame, max_scan: int = 20) -> int | None:
    for i in range(min(max_scan, len(df_raw))):
        row = df_raw.iloc[i].astype(str).map(_norm)
        has_codigo = row.str.contains(r"\bcod(?:igo)?\b", regex=True).any()
        has_desc   = row.str.contains("descric").any()
        if has_codigo and has_desc:
            return i
    return None

# ---------- Mapeamento de colunas ----------

_COL_CANDIDATES = {
    "codigo":    ("codigo", "código", "cod.", "cod"),
    "banco":     ("banco", "base", "fonte"),  # pode não existir em Composições
    "descricao": ("descricao", "descrição", "descr"),
    "valor_unit": ("valor unit", "valor unitario", "valor unitário",
                   "vlr unit", "val unit", "unitario", "valor"),
    "tipo":      ("tipo",),  # pode não ser a coluna real de tipo
}

def _build_lookup(columns: Iterable[str]) -> dict[str, str]:
    return {_norm(c): c for c in map(str, columns)}

def _pick_col(lookup: dict[str, str], candidates: Iterable[str], required: bool = True) -> str | None:
    for c in candidates:
        c_norm = _norm(c)
        if c_norm in lookup:
            return lookup[c_norm]
        for k in lookup:
            if c_norm and k.startswith(c_norm):
                return lookup[k]
    if required:
        raise KeyError(f"Não encontrei nenhuma coluna compatível com: {tuple(candidates)}")
    return None

def _detect_tipo_column(df: pd.DataFrame) -> str | None:
    """
    Encontra a coluna que contém marcadores 'Composição', 'Composição Auxiliar' ou 'Insumo'.
    1) tenta a coluna 'Tipo'
    2) varre demais colunas procurando esses marcadores
    """
    # 1) tenta 'Tipo'
    if "Tipo" in df.columns:
        vals = df["Tipo"].astype(str).map(_norm)
        if vals.str.contains(r"compos|insumo", regex=True, na=False).any():
            return "Tipo"
    # 2) varre colunas
    for c in df.columns:
        vals = df[c].astype(str).map(_norm)
        if vals.str.contains(r"compos|insumo", regex=True, na=False).any():
            return c
    return None

# ---------- Loader principal ----------

def load_orcamento(
    path: str,
    sheets: list[str | int] | None = None,  # se None, tenta "Composições"
    banco: str | None = None,               # se existir coluna
    valor_scale: float = 1.0,   
) -> CanonDict:
    """
    Lê a(s) aba(s) **Composições** e retorna Dict[codigo, Item] no esquema canônico,
    **filtrando apenas 'Composição' e 'Composição Auxiliar'** (usando a coluna real de tipo).
    """
    xls = pd.ExcelFile(path)

    if sheets is None:
        candidates = [s for s in xls.sheet_names if _looks_like_composicoes(s)]
        if not candidates:
            logger.warning("Nenhuma aba 'Composições' detectada; usando a primeira como fallback.")
            candidates = [xls.sheet_names[0]]
        sheets = candidates
        logger.info(f"Abas detectadas para Composições: {sheets}")

    frames: list[pd.DataFrame] = []

    for sheet in sheets:
        df_raw = pd.read_excel(path, sheet_name=sheet, header=None)
        header_row = _find_header_row(df_raw)
        if header_row is None:
            header_row = 4
            logger.warning(f"[{sheet}] Cabeçalho não detectado; usando header=4 (linha 5).")

        df = pd.read_excel(path, sheet_name=sheet, header=header_row)
        lookup = _build_lookup(df.columns)

        try:
            col_codigo   = _pick_col(lookup, _COL_CANDIDATES["codigo"])
            col_desc     = _pick_col(lookup, _COL_CANDIDATES["descricao"])
            col_val_unit = _pick_col(lookup, _COL_CANDIDATES["valor_unit"])
            col_banco    = _pick_col(lookup, _COL_CANDIDATES["banco"], required=False)
        except KeyError as e:
            logger.warning(f"[{sheet}] {e}; pulando aba.")
            continue

        # descobre a coluna real de tipo (pode ser 'Tipo' ou a primeira coluna sem nome)
        col_tipo = _detect_tipo_column(df)
        if col_tipo:
            logger.info(f"[{sheet}] Coluna de tipo detectada: {col_tipo!r}")
        else:
            logger.warning(f"[{sheet}] Não encontrei coluna de tipo; seguindo sem filtro por tipo.")

        cols = [col_codigo, col_desc, col_val_unit]
        new_names = ["CODIGO_ORC", "DESCRICAO_ORC", "VALOR_ORC"]
        if col_banco:
            cols.append(col_banco)
            new_names.append("BANCO")
        if col_tipo:
            cols.append(col_tipo)
            new_names.append("TIPO_REAL")

        proj = df[cols].copy()
        proj.columns = new_names

        # FILTRO: somente Composição / Composição Auxiliar (usando a coluna real)
        if "TIPO_REAL" in proj.columns:
            tipo_norm = proj["TIPO_REAL"].map(_norm)
            keep = tipo_norm.str.contains(r"\bcomposicao\b", regex=True, na=False)
            keep |= tipo_norm.str.contains(r"composicao\s+aux", regex=True, na=False)
            drop = (~keep).sum()
            logger.info(f"[{sheet}] Selecionando {keep.sum()} linhas de 'composição'; descartando {drop}.")
            proj = proj[keep]

        # limpeza
        proj["CODIGO_ORC"] = proj["CODIGO_ORC"].map(norm_code)
        proj["DESCRICAO_ORC"] = proj["DESCRICAO_ORC"].astype(str).str.strip()


        # garantir numérico e aplicar escala (ex.: 0.01 se vier 100x)
        proj["VALOR_ORC"] = pd.to_numeric(proj["VALOR_ORC"], errors="coerce")
        if valor_scale != 1.0:
            proj["VALOR_ORC"] = proj["VALOR_ORC"] * float(valor_scale)

        if banco and "BANCO" in proj.columns:
            alvo = _norm(banco)
            proj = proj[proj["BANCO"].map(_norm).eq(alvo)]

        proj = proj.dropna(subset=["CODIGO_ORC", "DESCRICAO_ORC"])
        frames.append(proj)

    if not frames:
        raise RuntimeError("Nenhuma aba de 'Composições' válida foi encontrada.")

    df_all = pd.concat(frames, ignore_index=True)
    
    # ---- construir Dict[chave_unica, Item] ----
    out: CanonDict = {}
    occ_counter: dict[str, int] = {}

    for _, row in df_all.iterrows():
        codigo_base = row["CODIGO_ORC"]

        # conta ocorrência deste código
        occ = occ_counter.get(codigo_base, 0) + 1
        occ_counter[codigo_base] = occ

        # chave única para esta ocorrência (não confundir com o código base)
        key = f"{codigo_base}__occ{occ}"

        item: Item = {
            "codigo": codigo_base,  # mantém o código 'real' aqui
            "descricao": row["DESCRICAO_ORC"],
            "valor_unit": float(row["VALOR_ORC"]) if pd.notna(row["VALOR_ORC"]) else 0.0,
            "fonte": "ORCAMENTO",
        }
        if "BANCO" in df_all.columns:
            item["banco"] = str(row.get("BANCO", "")).strip()

        out[key] = item

    # log opcional: quantos duplicados de fato existem
    dup_total = sum(occ - 1 for occ in occ_counter.values() if occ > 1)
    if dup_total:
        logger.info("ORÇAMENTO: %d ocorrência(s) duplicada(s) mantidas como entradas distintas.", dup_total)

    return out
