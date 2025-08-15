#!/usr/bin/env python3
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.abspath("src"))
import argparse
from cruzar_orcamento.adapters.estrutura_sudecap import load_estrutura_sudecap

def main():
    p = argparse.ArgumentParser(description="Teste: estrutura SUDECAP (pai + filhos de 1º nível).")
    p.add_argument("--ref", required=True, help="Arquivo SUDECAP (.xls/.xlsx)")
    p.add_argument("--preview", type=int, default=5, help="Quantidade de pais para mostrar (preview).")
    args = p.parse_args()

    print("== Testando estrutura SUDECAP ==")
    print(f"Arquivo: {args.ref}")

    est = load_estrutura_sudecap(args.ref)

    pais = list(est.values())
    total_filhos = sum(len(c["filhos"]) for c in pais)
    print(f"Total de composições (pais): {len(pais)}")
    print(f"Total de filhos (1º nível): {total_filhos}\n")
    print(f"Preview dos primeiros {min(args.preview, len(pais))} pais:\n")

    for i, pai in enumerate(pais[:args.preview], 1):
        print(f"[{i}] PAI {pai['codigo']} — {pai['descricao']}")
        for j, ch in enumerate(pai["filhos"], 1):
            print(f"   - filho #{j}: {ch['codigo']} — {ch['descricao']}")
        print()

    print("OK ✅")

if __name__ == "__main__":
    main()
