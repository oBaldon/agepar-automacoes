# scripts/test_secid_estrutura.py
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

# Import flexível (dependendo de como você nomeou no adapter)
try:
    from src.cruzar_orcamento.adapters.estrutura_secid import (
        load_estrutura_secid as load_estrutura,
    )
except Exception:
    from src.cruzar_orcamento.adapters.estrutura_secid import (
        load_estrutura_secid_analitico as load_estrutura,  # fallback
    )


def _trunc(s: Any, n: int = 100) -> str:
    s = "" if s is None else str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def main():
    ap = argparse.ArgumentParser(
        description="Teste rápido do loader de ESTRUTURA da SECID"
    )
    ap.add_argument("arquivo", help="Caminho do .xlsx da SECID (estrutura)")
    ap.add_argument(
        "-n", "--sample", type=int, default=10, help="Quantidade de pais para mostrar (default: 10)"
    )
    ap.add_argument(
        "-c", "--children", type=int, default=5, help="Qtde de filhos para listar por pai (default: 5)"
    )
    args = ap.parse_args()

    path = Path(args.arquivo).expanduser().resolve()
    print(f"Arquivo: {path}")

    estr = load_estrutura(path)

    # O adapter deve retornar um "dicionário" {codigo_pai -> {codigo, descricao, filhos:[...]}}
    # mas deixamos tolerante: se vier lista, transformamos num dict por 'codigo'
    if isinstance(estr, list):
        tmp = {}
        for comp in estr:
            codigo = comp.get("codigo") if isinstance(comp, dict) else getattr(comp, "codigo", None)
            if codigo:
                tmp[codigo] = comp
        estr = tmp

    if not isinstance(estr, dict):
        raise SystemExit("Retorno inesperado do loader. Esperado dict ou lista de comps.")

    n_pais = len(estr)
    total_filhos = 0
    for comp in estr.values():
        filhos = comp.get("filhos") if isinstance(comp, dict) else getattr(comp, "filhos", [])
        total_filhos += len(filhos or [])

    print(f"Pais (itens de 1º nível): {n_pais}")
    print(f"Total de vínculos pai→filho: {total_filhos}")

    # Ordena pelos códigos e mostra amostra
    codes_sorted = sorted(estr.keys())
    print("\n=== Amostra ===")
    for codigo in codes_sorted[: args.sample]:
        comp = estr[codigo]
        desc = comp.get("descricao") if isinstance(comp, dict) else getattr(comp, "descricao", "")
        filhos = comp.get("filhos") if isinstance(comp, dict) else getattr(comp, "filhos", [])
        print(f"\n{codigo}  { _trunc(desc, 110) }")
        if not filhos:
            print("  (sem filhos)")
            continue
        for f in (filhos or [])[: args.children]:
            if isinstance(f, dict):
                c = f.get("codigo")
                d = f.get("descricao")
            else:
                c = getattr(f, "codigo", "")
                d = getattr(f, "descricao", "")
            print(f"  - {c:<12}  {_trunc(d, 100)}")


if __name__ == "__main__":
    main()
