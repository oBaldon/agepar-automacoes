# src/cruzar_orcamento/exporters/json_estrutura.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json


def export_estrutura_divergencias_json(
    divergencias: List[Dict[str, Any]],
    path: str | Path,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
    meta: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Salva um JSON com as divergências de ESTRUTURA (pais/filhos 1º nível).

    Formato:
    {
      "total_divergencias": <int>,
      "divergencias": [ ... ],
      "meta": { ... }               # opcional
    }
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = {
        "total_divergencias": len(divergencias),
        "divergencias": divergencias,
    }
    if meta:
        payload["meta"] = meta

    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=ensure_ascii, indent=indent)

    return out


def export_estruturas_brutas_json(
    estrutura_a: Dict[str, Any],
    estrutura_b: Dict[str, Any],
    path: str | Path,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
    meta: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    (Opcional) Salva as duas estruturas completas (A e B) para depuração/inspeção.

    Cuidado: pode gerar arquivos grandes.

    Formato:
    {
      "A": { ... estrutura do orçamento filtrada ... },
      "B": { ... estrutura da base ... },
      "meta": { ... }               # opcional
    }
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = {
        "A": estrutura_a,
        "B": estrutura_b,
    }
    if meta:
        payload["meta"] = meta

    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=ensure_ascii, indent=indent)

    return out
