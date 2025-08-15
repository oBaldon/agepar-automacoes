# src/cruzar_orcamento/adapters/sudecap.py
from __future__ import annotations

import logging
from typing import Iterable
import unicodedata
import pandas as pd

from ..models import Item, CanonDict
from ..utils.utils_text import norm_code

logger = logging.getLogger(__name__)

# ---------- Heurísticas de detecção ----------

def _strip_accents(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()

def _norm(s: str) -> str:
    if not isinstance(s, str):
        s = "" if pd.isna(s) else str(s)
    s = _strip_accents(s).lower().strip()
    return s

def _find_header_row(df_raw: pd.DataFrame, max_scan: int = 20) -> int | None:
    """
    Procura uma linha de cabeçalho contendo algo como:
    - codigo/código e descricao/descrição
    """
    for i in range(min(max_scan, len(df_raw))):
        row = df_raw.iloc[i].astype(str).map(_norm)
        has_codigo = row.str.contains(r"\bcod(?:igo)?\b", regex=True).any()
        has_desc   = row.str.contains("descric").any()
        if has_codigo and has_desc:
            return i
    return None

# ---------- Mapeamento de colunas ----------

_COL_CANDIDATES = {
    "codigo": ("codigo", "código", "cod.", "cod", "codigo sudecap", "código sudecap"),
    "descricao": ("descricao", "descrição", "descr", "descricao sudecap", "descrição sudecap"),
    # muitos arquivos SUDECAP vêm com "VALOR" puro
    "valor_unit": ("valor unit", "valor unitario", "valor unitário", "vlr unit", "val unit", "unitario", "valor"),
}

def _build_lookup(columns: Iterable[str]) -> dict[str, str]:
    return {_norm(c): c for c in map(str, columns)}

def _pick_col(lookup: dict[str, str], candidates: Iterable[str]) -> str:
    for c in candidates:
        c_norm = _norm(c)
        # match direto
        if c_norm in lookup:
            return lookup[c_norm]
        # match por prefixo (ex.: "valor unit" == "valor unit com bdi")
        for k in lookup:
            if c_norm and k.startswith(c_norm):
                return lookup[k]
    raise KeyError(f"Não encontrei nenhuma coluna compatível com: {tuple(candidates)}")

# ---------- Loader principal ----------

def load_sudecap(
    path: str,
    sheet: str | int | None = None,
) -> CanonDict:
    """
    Lê planilha SUDECAP e retorna Dict[codigo, Item] no esquema canônico.

    - Usa a primeira aba por padrão (sheet=0), a menos que você especifique outra.
    - Detecta cabeçalho automaticamente (scaneando as primeiras linhas; fallback header=4).
    - Mapeia nomes de colunas de forma flexível (aceita 'VALOR').
    - Converte vírgula decimal para ponto quando necessário.
    """
    xls = pd.ExcelFile(path)

    # Usa a primeira aba por padrão, a menos que o usuário especifique
    if sheet is None:
        sheet = 0
        logger.info(f"Aba detectada para SUDECAP: {sheet!r}")

    df_raw = pd.read_excel(path, sheet_name=sheet, header=None)
    header_row = _find_header_row(df_raw)
    if header_row is None:
        # fallback comum: linha 5 (index 4)
        header_row = 4
        logger.warning(f"[{sheet}] Cabeçalho não detectado; usando header=4 (linha 5).")

    df = pd.read_excel(path, sheet_name=sheet, header=header_row)

    lookup = _build_lookup(df.columns)

    try:
        col_codigo   = _pick_col(lookup, _COL_CANDIDATES["codigo"])
        col_desc     = _pick_col(lookup, _COL_CANDIDATES["descricao"])
        col_val_unit = _pick_col(lookup, _COL_CANDIDATES["valor_unit"])
    except KeyError as e:
        raise KeyError(f"[{sheet}] {e}. Colunas disponíveis: {list(df.columns)}") from e

    proj = df[[col_codigo, col_desc, col_val_unit]].copy()
    proj.columns = ["CODIGO_SUDECAP", "DESCRICAO_SUDECAP", "VALOR_SUDECAP"]

    # limpeza
    proj["CODIGO_SUDECAP"] = proj["CODIGO_SUDECAP"].map(norm_code)  # não forçar str pra evitar "nan"
    proj["DESCRICAO_SUDECAP"] = proj["DESCRICAO_SUDECAP"].astype(str).str.strip()

    # tratamento de vírgula/milhar em VALOR_SUDECAP antes de to_numeric
    if proj["VALOR_SUDECAP"].dtype == object:
        proj["VALOR_SUDECAP"] = (
            proj["VALOR_SUDECAP"]
            .astype(str)
            .str.replace(".", "", regex=False)     # remove separador de milhar comum
            .str.replace(",", ".", regex=False)    # vírgula -> ponto
        )
    proj["VALOR_SUDECAP"] = pd.to_numeric(proj["VALOR_SUDECAP"], errors="coerce")

    # descartar linhas sem código/descrição
    proj = proj.dropna(subset=["CODIGO_SUDECAP", "DESCRICAO_SUDECAP"])

    # ---- construir Dict[codigo, Item] ----
    out: CanonDict = {}
    dup_count = 0
    for _, row in proj.iterrows():
        codigo = row["CODIGO_SUDECAP"]
        item: Item = {
            "codigo": codigo,
            "descricao": row["DESCRICAO_SUDECAP"],
            "valor_unit": float(row["VALOR_SUDECAP"]) if pd.notna(row["VALOR_SUDECAP"]) else 0.0,
            "fonte": "SUDECAP",
        }
        if codigo in out:
            dup_count += 1
            logger.warning(
                "Código duplicado detectado na SUDECAP: %r (substituindo %r → %r)",
                codigo, out[codigo]["descricao"], item["descricao"]
            )
        out[codigo] = item

    if dup_count:
        logger.warning("SUDECAP: detectados %d código(s) duplicado(s); mantendo o último.", dup_count)

    return out
