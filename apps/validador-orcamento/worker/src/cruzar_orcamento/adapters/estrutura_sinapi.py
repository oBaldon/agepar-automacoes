# src/cruzar_orcamento/adapters/estrutura_sinapi.py
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from ..models import CompEstrutura, ChildSpec, EstruturaDict
from ..utils.utils_code import norm_code_canonical

logger = logging.getLogger(__name__)


def _strip(v) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()


def _find_header_row(df_raw: pd.DataFrame, max_scan: int = 25) -> Optional[int]:
    """
    Tenta localizar o cabeçalho procurando por 'Descrição' em alguma coluna,
    pois na aba Analítico o header normalmente existe. Se não achar, usa None (posicional).
    """
    for i in range(min(max_scan, len(df_raw))):
        row = df_raw.iloc[i].astype(str).str.lower()
        if row.str.contains("descri", regex=False).any():
            return i
    return None


def load_estrutura_sinapi_analitico(path: str, sheet_name: str = "Analítico") -> EstruturaDict:
    """
    Lê a aba 'Analítico' do SINAPI e constrói:
      { codigo_pai: {codigo, descricao, filhos:[{codigo, descricao}], fonte:'SINAPI'} }

    Convenção (confirmada no projeto):
      - Código do PAI    → coluna B (índice 1, 0-based)
      - Tipo do FILHO    → coluna C (índice 2) — valores típicos: 'INSUMO' / 'COMPOSICAO'
      - Código do FILHO  → coluna D (índice 3)
      - Descrição        → procurar coluna 'Descrição' pelo cabeçalho; se não houver,
                           usar a coluna E (índice 4) como fallback para descrição da linha.

    Observações:
      - O arquivo pode conter valores numéricos que viram 'xxxxx.0'; usamos `norm_code_canonical`.
      - Não “explode” composições auxiliares: apenas registra filhos de 1º nível.
    """
    # 1) Detecta header (se houver) para pegar 'Descrição' com nome, mas sem depender dele pros códigos
    df_raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    header_row = _find_header_row(df_raw)

    desc_col = None
    if header_row is not None:
        df = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
        cols_lower = {str(c).strip().lower(): c for c in df.columns}
        # tenta achar alguma coluna de descrição
        for k, real in cols_lower.items():
            if "descri" in k:
                desc_col = real
                break
        # se não achou, volta para leitura sem header e usa posicional
        if desc_col is None:
            logger.warning("[SINAPI Analítico] Coluna de descrição não localizada pelo header; usando posicional.")
            df = df_raw.copy()
            header_row = None
    else:
        df = df_raw.copy()

    # 2) Função auxiliar para descrever a linha atual
    def get_desc(row) -> str:
        if header_row is not None and desc_col is not None:
            return _strip(row.get(desc_col))
        # fallback: coluna E (idx 4) costuma ser a descrição do item/linha
        try:
            return _strip(row.iloc[4])
        except Exception:
            return ""

    out: EstruturaDict = {}
    pai_atual: Optional[CompEstrutura] = None
    total_filhos = 0

    # 3) Varre linhas
    for _, row in df.iterrows():
        # B, C, D por índice (garantido mesmo sem header)
        try:
            cod_pai_raw = _strip(row.iloc[1])  # B
        except Exception:
            cod_pai_raw = ""
        try:
            tipo_raw = _strip(row.iloc[2])     # C
        except Exception:
            tipo_raw = ""
        try:
            cod_filho_raw = _strip(row.iloc[3])  # D
        except Exception:
            cod_filho_raw = ""

        cod_pai = norm_code_canonical(cod_pai_raw)
        tipo = tipo_raw.casefold()
        cod_filho = norm_code_canonical(cod_filho_raw)

        # linha vazia? segue
        if not cod_pai and not cod_filho and not tipo:
            continue

        # Sempre que aparecer um novo código em B, considera-se “começo/continuidade” de um pai
        if cod_pai:
            if (pai_atual is None) or (pai_atual["codigo"] != cod_pai):
                # fecha o anterior
                if pai_atual is not None:
                    out[pai_atual["codigo"]] = pai_atual
                # inicia novo pai
                pai_atual = CompEstrutura(
                    codigo=cod_pai,
                    descricao=get_desc(row),   # descrição do pai na própria linha do pai
                    filhos=[],
                    fonte="SINAPI",
                )

        # Se temos um pai atual e a coluna D (filho) está preenchida,
        # registra filho quando tipo for INSUMO/COMPOSICAO
        if pai_atual and cod_filho and (("insumo" in tipo) or ("composicao" in tipo) or ("composição" in tipo)):
            filho_desc = get_desc(row)
            filho: ChildSpec = {"codigo": cod_filho, "descricao": filho_desc}
            pai_atual["filhos"].append(filho)
            total_filhos += 1

    # fecha o último pai
    if pai_atual:
        out[pai_atual["codigo"]] = pai_atual

    logger.info(
        "[SINAPI Analítico] Estrutura construída: %d composição(ões) com %d filho(s) no total.",
        len(out), total_filhos
    )
    return out
