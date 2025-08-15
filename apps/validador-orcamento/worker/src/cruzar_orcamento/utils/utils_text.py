from __future__ import annotations

import re
import unicodedata
import pandas as pd


def strip_accents(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def norm_text(s: str | float | int | None) -> str:
    """
    Normaliza texto para comparações:
    - converte para string
    - remove acentos
    - lower/casefold
    - remove pontuação/ruído
    - colapsa múltiplos espaços
    """
    if not isinstance(s, str):
        s = "" if s is None or (isinstance(s, float) and pd.isna(s)) else str(s)
    s = strip_accents(s).casefold()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_code(s: str | float | int | None) -> str:
    """
    Normaliza código (chave de cruzamento):
    - string + strip; NÃO remove zeros à esquerda (importante!)
    - se vier NaN/None, retorna string vazia
    """
    if not isinstance(s, str):
        if s is None or (isinstance(s, float) and pd.isna(s)):
            return ""
        s = str(s)
    return s.strip()
