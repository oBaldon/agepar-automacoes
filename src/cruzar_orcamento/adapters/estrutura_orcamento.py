# src/cruzar_orcamento/adapters/estrutura_orcamento.py
from __future__ import annotations

import logging
from typing import Iterable, List, Optional
import unicodedata
import pandas as pd

from ..models import EstruturaDict, CompEstrutura, ChildSpec
from ..utils.utils_code import norm_code_canonical  # normalizador de códigos

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
    """Tenta localizar a linha de cabeçalho pela presença de 'código' e 'descrição'."""
    for i in range(min(max_scan, len(df_raw))):
        row = df_raw.iloc[i].astype(str).map(_norm)
        has_codigo = row.str.contains(r"\bcod(?:igo)?\b", regex=True, na=False).any()
        has_desc   = row.str.contains("descric", na=False).any()
        if has_codigo and has_desc:
            return i
    return None

# ---------- Mapeamento de colunas ----------

_COL_CANDIDATES = {
    "codigo":    ("codigo", "código", "cod.", "cod"),
    "descricao": ("descricao", "descrição", "descr"),
    "tipo":      ("tipo",),  # pode não ser exatamente 'Tipo'; vamos detectar
    "banco":     ("banco", "base", "fonte"),  # coluna opcional para filtro por banco
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

def _detect_tipo_column(df: pd.DataFrame) -> Optional[str]:
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

# ---------- Loader de estrutura (pai + filhos 1º nível) ----------

def load_estrutura_orcamento(
    path: str,
    sheets: List[str | int] | None = None,
    banco: str | None = None,   # <-- filtro opcional por banco (aplicado no PAI)
) -> EstruturaDict:
    """
    Lê a(s) aba(s) de **Composições** do ORÇAMENTO e monta a estrutura:
      - Pai = linha com tipo 'Composição'
      - Filhos = linhas seguintes com 'Composição Auxiliar' ou 'Insumo', até a próxima 'Composição'

    Se `banco` for informado, mantém apenas PAIS cuja linha (de 'Composição') tenha a coluna BANCO/Base/Fonte
    igual ao banco desejado (case-insensitive). Se a coluna de banco não existir, o filtro é ignorado nessa aba.

    Retorna um EstruturaDict: {codigo_pai: {codigo, descricao, filhos[], fonte="ORCAMENTO"}}
    """
    xls = pd.ExcelFile(path)

    # escolher abas
    if sheets is None:
        candidates = [s for s in xls.sheet_names if _looks_like_composicoes(s)]
        if not candidates:
            logger.warning("Nenhuma aba 'Composições' detectada; usando a primeira como fallback.")
            candidates = [xls.sheet_names[0]]
        sheets = candidates
        logger.info(f"Abas detectadas para Composições: {sheets}")

    estruturas: EstruturaDict = {}
    pais_detectados = 0
    filhos_detectados = 0
    pais_duplicados = 0

    alvo_banco_norm = _norm(banco) if banco else None

    for sheet in sheets:
        # localizar header
        df_raw = pd.read_excel(path, sheet_name=sheet, header=None)
        header_row = _find_header_row(df_raw)
        if header_row is None:
            header_row = 4
            logger.warning(f"[{sheet}] Cabeçalho não detectado; usando header=4 (linha 5).")

        df = pd.read_excel(path, sheet_name=sheet, header=header_row)
        lookup = _build_lookup(df.columns)

        try:
            col_codigo = _pick_col(lookup, _COL_CANDIDATES["codigo"])
            col_desc   = _pick_col(lookup, _COL_CANDIDATES["descricao"])
            col_banco  = _pick_col(lookup, _COL_CANDIDATES["banco"], required=False)  # opcional
        except KeyError as e:
            logger.warning(f"[{sheet}] {e}; pulando aba.")
            continue

        col_tipo = _detect_tipo_column(df)
        if col_tipo:
            logger.info(f"[{sheet}] Coluna de tipo detectada: {col_tipo!r}")
        else:
            logger.error(f"[{sheet}] Não encontrei coluna de tipo; não é possível montar a estrutura.")
            continue

        # projeção e limpeza base
        cols = [col_codigo, col_desc, col_tipo]
        newcols = ["CODIGO", "DESCRICAO", "TIPO"]
        if col_banco:
            cols.append(col_banco)
            newcols.append("BANCO")

        proj = df[cols].copy()
        proj.columns = newcols

        # Normalizações
        proj["CODIGO"] = proj["CODIGO"].map(norm_code_canonical)
        proj["DESCRICAO"] = proj["DESCRICAO"].astype(str).str.strip()
        tipo_norm = proj["TIPO"].astype(str).map(_norm)

        # flags
        is_pai     = tipo_norm.str.fullmatch(r".*\bcomposicao\b.*", na=False) & ~tipo_norm.str.contains("aux", na=False)
        is_aux     = tipo_norm.str.contains(r"composicao\s*aux", regex=True, na=False)
        is_insumo  = tipo_norm.str.contains(r"\binsumo\b", regex=True, na=False)

        if banco and ("BANCO" not in proj.columns):
            logger.warning(f"[{sheet}] Filtro por banco={banco!r} solicitado, mas coluna de banco não encontrada; ignorando filtro nesta aba.")

        # varredura sequencial: ao achar PAI, começa grupo; filhos acumulam até próximo PAI
        current_pai: Optional[CompEstrutura] = None

        for idx, row in proj.iterrows():
            codigo = row["CODIGO"]
            desc   = row["DESCRICAO"]

            if is_pai.loc[idx]:  # nova composição mestra
                # fechar pai anterior, se houver
                if current_pai is not None and current_pai["codigo"]:
                    cod_pai_prev = current_pai["codigo"]
                    if cod_pai_prev in estruturas:
                        pais_duplicados += 1
                        logger.warning(
                            f"[{sheet}] Código de composição duplicado detectado (estrutura): {cod_pai_prev!r} "
                            f"(substituindo '{estruturas[cod_pai_prev]['descricao']}' → '{current_pai['descricao']}')"
                        )
                    estruturas[cod_pai_prev] = current_pai

                # aplicar filtro por banco no PAI (se solicitado e houver coluna)
                if alvo_banco_norm and ("BANCO" in proj.columns):
                    row_banco_norm = _norm(row.get("BANCO", ""))
                    if row_banco_norm != alvo_banco_norm:
                        # ignorar este pai (fora do banco alvo)
                        current_pai = None
                        continue

                # inicia novo pai
                current_pai = CompEstrutura(
                    codigo=str(codigo) if pd.notna(codigo) else "",
                    descricao=str(desc) if pd.notna(desc) else "",
                    filhos=[],          # preencheremos a seguir
                    fonte="ORCAMENTO",
                )
                pais_detectados += 1
                continue

            # se não é pai, pode ser filho (insumo ou comp. auxiliar)
            if current_pai is not None and (is_aux.loc[idx] or is_insumo.loc[idx]):
                if pd.notna(codigo) and str(codigo).strip():
                    filho: ChildSpec = {
                        "codigo": norm_code_canonical(codigo),  # normaliza também o filho
                        "descricao": str(desc) if pd.notna(desc) else "",
                    }
                    current_pai["filhos"].append(filho)
                    filhos_detectados += 1
                continue

            # demais linhas (totais, vazias, cabeçalhos internos etc.) ignoramos.

        # ao final da aba, se houver pai em aberto, salvar
        if current_pai is not None and current_pai["codigo"]:
            cod_pai = current_pai["codigo"]
            if cod_pai in estruturas:
                pais_duplicados += 1
                logger.warning(
                    f"[{sheet}] Código de composição duplicado detectado (estrutura): {cod_pai!r} "
                    f"(substituindo '{estruturas[cod_pai]['descricao']}' → '{current_pai['descricao']}')"
                )
            estruturas[cod_pai] = current_pai

    logger.info(
        "Estrutura ORÇAMENTO construída: %d composição(ões) com %d filho(s) no total. Duplicados de pai: %d.",
        len(estruturas), filhos_detectados, pais_duplicados
    )

    return estruturas
