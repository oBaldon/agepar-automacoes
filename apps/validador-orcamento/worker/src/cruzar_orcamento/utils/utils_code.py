# src/cruzar_orcamento/utils/utils_code.py
from __future__ import annotations

import re

def norm_code_canonical(x: object) -> str:
    """
    Normaliza códigos para uma forma canônica, visando comparação estável:
      - Remove sufixo ".0" (ou ".00...") típico de exportação do Excel.
      - Remove zeros à esquerda de segmentos numéricos.
      - Preserva segmentação por pontos (ex.: "01.02.003" -> "1.2.3").
      - Trata valores vazios, None e strings "nan" como vazio "".

    Exemplos:
      "37370.0"         -> "37370"
      "00037370"        -> "37370"
      "01.02.003"       -> "1.2.3"
      "B.01.000.010116" -> "B.1.0.10116"   (somente segmentos totalmente numéricos perdem zeros à esquerda)
      88316.0           -> "88316"
      "nan"             -> ""
    """
    if x is None:
        return ""

    s = str(x).strip()
    if s == "" or s.lower() in ("nan", "none"):
        return ""

    # Caso 1: número inteiro possivelmente com ".0", ".00", etc. (tudo dígito + .0+)
    m = re.fullmatch(r"(\d+)(?:\.0+)?", s)
    if m:
        num = m.group(1)
        return num.lstrip("0") or "0"

    # Caso 2: código segmentado por pontos (ex.: "01.02.003" | "B.01.000.010116")
    if "." in s:
        parts = s.split(".")
        norm_parts = []
        for p in parts:
            p = p.strip()
            if p.isdigit():
                norm_parts.append(p.lstrip("0") or "0")
            else:
                # Segmento não-estritamente numérico: mantém como está
                norm_parts.append(p)
        return ".".join(norm_parts)

    # Caso 3: apenas dígitos (com possíveis zeros à esquerda)
    if s.isdigit():
        return s.lstrip("0") or "0"

    # Caso 4: string numérica genérica que vira float, mas sem padrão .0 (ex.: "88316.000")
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
    except Exception:
        pass

    # Fallback: retorna a string original
    return s
