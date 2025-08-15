#!/usr/bin/env python3
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.abspath("src"))
import argparse

from cruzar_orcamento.adapters.estrutura_sinapi import load_estrutura_sinapi_analitico

def main():
    p = argparse.ArgumentParser(description="Testa extração de estrutura do SINAPI (aba Analítico).")
    p.add_argument("--ref", required=True, help="Arquivo SINAPI_YYYY_MM.xlsx")
    p.add_argument("--limit", type=int, default=5, help="Quantos pais mostrar no preview (default 5)")
    args = p.parse_args()

    est = load_estrutura_sinapi_analitico(args.ref)

    pais = list(est.keys())
    print("== Testando estrutura SINAPI (Analítico) ==")
    print(f"Arquivo: {args.ref}")
    print(f"Total de composições (pais): {len(pais)}")
    total_filhos = sum(len(est[c]["filhos"]) for c in pais)
    print(f"Total de filhos (1º nível): {total_filhos}\n")

    print(f"Preview dos primeiros {min(args.limit, len(pais))} pais:\n")
    for i, cod in enumerate(pais[:args.limit], start=1):
        pai = est[cod]
        print(f"[{i}] PAI {pai['codigo']} — {pai['descricao']}")
        for j, f in enumerate(pai["filhos"][:10], start=1):
            print(f"   - filho #{j}: {f['codigo']} — {f['descricao']}")
        if len(pai["filhos"]) > 10:
            print(f"   … (+{len(pai['filhos'])-10} filhos)")
        print()

    print("OK ✅")

if __name__ == "__main__":
    main()
