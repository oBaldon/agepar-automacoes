# src/cruzar_orcamento/exporters/json_prices.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple
import json

def export_precos_json(
    cruzado: List[Dict[str, Any]],
    divergencias: List[Dict[str, Any]],
    path: str | Path,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> Path:
    """
    Salva um JSON no formato:
    {
      "cruzado": [...],
      "divergencias": [...]
    }
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cruzado": cruzado,
        "divergencias": divergencias,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=ensure_ascii, indent=indent)
    return out
