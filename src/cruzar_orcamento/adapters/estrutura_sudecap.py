# src/cruzar_orcamento/adapters/estrutura_sudecap.py
from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd

from ..models import EstruturaDict, CompEstrutura, ChildSpec
from ..utils.utils_code import norm_code_canonical

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------
# Heurísticas / helpers
# --------------------------------------------------------------------

def _strip(v) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()

def _norm(s: str) -> str:
    return _strip(s).casefold()

def _looks_like_header_row(row: pd.Series) -> bool:
    """
    Linha de cabeçalho típica do relatório SUDECAP tem algo como:
      - 'CÓDIGO'
      - 'CÓDIGO / DESCRIÇÃO' (ou 'DESCRIÇÃO')
      - 'UND' ou 'CONSUMO'
    """
    vals = row.astype(str).map(_norm)
    has_codigo = vals.str.contains("código|codigo|^cod\\.?$", regex=True, na=False).any()
    has_desc   = vals.str.contains("descr", na=False).any()
    has_und_or_consumo = vals.str.contains(r"\bund\b|consumo", regex=True, na=False).any()
    return has_codigo and has_desc and has_und_or_consumo

def _find_header_row(df_raw: pd.DataFrame, max_scan: int = 40) -> Optional[int]:
    for i in range(min(max_scan, len(df_raw))):
        if _looks_like_header_row(df_raw.iloc[i]):
            return i
    return None

def _join_desc(parts: list[str]) -> str:
    """Junta partes de descrição, ignorando vazios/NaN, normalizando espaços."""
    tokens = [p for p in ( _strip(x) for x in parts ) if p]
    return " ".join(tokens)

# --------------------------------------------------------------------
# Loader principal
# --------------------------------------------------------------------

def load_estrutura_sudecap(path: str, sheets: List[str | int] | None = None) -> EstruturaDict:
    """
    Lê XLS do SUDECAP (Relatório de Composições).

    Convenção confirmada (arquivo Abril/2025):
      - Coluna A (idx 0): CÓDIGO da COMPOSIÇÃO PAI
      - Coluna B (idx 1): Para linha de PAI → descrição do pai
                          Para linha de FILHO → CÓDIGO do FILHO
      - Colunas C..G (idx 2..6): Demais partes de texto (descrição), unidade etc.
        Para PAI: descrição = junção de B..G
        Para FILHO: descrição = junção de C..G

    Não “explode” composições auxiliares: registra somente filhos 1º nível.
    Retorna: {codigo_pai: {codigo, descricao, filhos:[{codigo,descricao}], fonte:"SUDECAP"}}
    """
    xls = pd.ExcelFile(path)
    if sheets is None:
        sheets = xls.sheet_names  # varre todas as abas

    estruturas: EstruturaDict = {}
    pais_detectados = 0
    filhos_detectados_total = 0
    pais_duplicados = 0

    for sheet in sheets:
        # 1) detectar header
        df_raw = pd.read_excel(path, sheet_name=sheet, header=None)
        header_row = _find_header_row(df_raw)
        if header_row is None:
            # Palpite razoável (linha 5 visivelmente comum), mas tentaremos mesmo assim
            header_row = 4
            logger.warning(f"[SUDECAP/{sheet}] Cabeçalho não detectado; usando header=4 (linha 5).")

        df = pd.read_excel(path, sheet_name=sheet, header=header_row)
        if df.empty:
            logger.warning(f"[SUDECAP/{sheet}] Aba vazia; pulando.")
            continue

        # 2) Usamos POSIÇÃO das colunas para evitar depender de títulos variáveis
        #    idx 0 = A, 1 = B, 2..6 = C..G (se existirem)
        col_count = df.shape[1]

        def col(idx: int):
            # acessa por posição com fallback seguro
            try:
                return df.iloc[:, idx]
            except Exception:
                # coluna inexistente → série vazia para não quebrar
                return pd.Series([], dtype=object)

        colA = col(0)  # código do pai
        colB = col(1)  # descrição do pai OU código do filho
        # colunas C..G para descrição (filho) / complemento (pai)
        cols_C_to_G = [col(i) for i in range(2, min(7, col_count))]

        # 3) Varredura
        current_pai: Optional[CompEstrutura] = None
        filhos_detectados_sheet = 0

        for i in range(len(df)):
            valA = _strip(colA.iloc[i]) if i < len(colA) else ""
            valB = _strip(colB.iloc[i]) if i < len(colB) else ""
            extra_parts = [series.iloc[i] if i < len(series) else "" for series in cols_C_to_G]

            code_pai = norm_code_canonical(valA)

            if code_pai:
                # Linha é PAI: fecha pai anterior e inicia um novo
                if current_pai is not None and current_pai["codigo"]:
                    cod_pai = current_pai["codigo"]
                    if cod_pai in estruturas:
                        pais_duplicados += 1
                        logger.warning(
                            f"[SUDECAP/{sheet}] Código de composição duplicado (estrutura): {cod_pai!r} "
                            f"(substituindo '{estruturas[cod_pai]['descricao']}' → '{current_pai['descricao']}')"
                        )
                    estruturas[cod_pai] = current_pai

                # descrição do pai = B..G
                desc_pai = _join_desc([valB, *extra_parts])
                current_pai = CompEstrutura(
                    codigo=code_pai,
                    descricao=desc_pai,
                    filhos=[],
                    fonte="SUDECAP",
                )
                pais_detectados += 1
                continue

            # Se NÃO é pai, pode ser FILHO: código do filho em B, descrição em C..G
            if current_pai is not None and valB:
                code_filho = norm_code_canonical(valB)
                if code_filho:
                    desc_filho = _join_desc(extra_parts)
                    # Evita cadastrar linhas que não tenham nenhuma descrição significativa
                    # (não é obrigatório, mas ajuda a filtrar ruídos)
                    if code_filho or desc_filho:
                        filho: ChildSpec = {
                            "codigo": code_filho,
                            "descricao": desc_filho,
                        }
                        current_pai["filhos"].append(filho)
                        filhos_detectados_sheet += 1
                        continue

            # Outras linhas (separadores, vazias, totais etc.) são ignoradas

        # Fecha o último pai da aba
        if current_pai is not None and current_pai["codigo"]:
            cod_pai = current_pai["codigo"]
            if cod_pai in estruturas:
                pais_duplicados += 1
                logger.warning(
                    f"[SUDECAP/{sheet}] Código de composição duplicado (estrutura): {cod_pai!r} "
                    f"(substituindo '{estruturas[cod_pai]['descricao']}' → '{current_pai['descricao']}')"
                )
            estruturas[cod_pai] = current_pai

        filhos_detectados_total += filhos_detectados_sheet

    logger.info(
        "Estrutura SUDECAP construída: %d composição(ões) com %d filho(s) no total. Duplicados de pai: %d.",
        len(estruturas),
        filhos_detectados_total,
        pais_duplicados,
    )
    return estruturas
