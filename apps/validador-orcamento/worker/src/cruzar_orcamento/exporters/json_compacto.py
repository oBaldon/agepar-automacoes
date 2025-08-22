# src/cruzar_orcamento/exporters/json_compacto.py
from __future__ import annotations
from pathlib import Path
import json, os, tempfile

def export_json(payload: dict, out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # escreve em arquivo temporário (atômico)…
    with tempfile.NamedTemporaryFile("w", delete=False, dir=out.parent, encoding="utf-8") as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name

    # …e garante permissões legíveis por outros (0644) antes do rename
    os.chmod(tmp_name, 0o644)
    os.replace(tmp_name, out)
    return out
