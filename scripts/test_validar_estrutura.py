#!/usr/bin/env python3
from __future__ import annotations

import sys, os, json
sys.path.insert(0, os.path.abspath("src"))
import argparse

from cruzar_orcamento.adapters.estrutura_orcamento import load_estrutura_orcamento
from cruzar_orcamento.adapters.estrutura_sinapi import load_estrutura_sinapi_analitico
from cruzar_orcamento.adapters.estrutura_sudecap import load_estrutura_sudecap
from cruzar_orcamento.validators.estrutura_compare import comparar_estruturas


def main():
    p = argparse.ArgumentParser(
        description=(
            "Valida a ESTRUTURA (pais/filhos 1º nível) do ORÇAMENTO contra uma BASE "
            "(ORCAMENTO, SINAPI Analítico ou SUDECAP Relatório)."
        )
    )
    p.add_argument("--orc", required=True, help="Arquivo do ORÇAMENTO (aba(s) de Composições).")
    p.add_argument("--banco-a", default="", help="Filtrar no ORÇAMENTO apenas pais deste banco (ex.: SINAPI, SUDECAP).")
    p.add_argument("--base", required=True, help="Arquivo da base de referência (ORÇAMENTO, SINAPI_YYYY_MM.xlsx ou SUDECAP_*.xls).")
    p.add_argument(
        "--base-type",
        choices=["ORCAMENTO", "SINAPI", "SUDECAP"],
        required=True,
        help="Tipo da base: ORCAMENTO (mesmo parser do orçamento), SINAPI (aba Analítico) ou SUDECAP (Relatório de Composições)."
    )
    p.add_argument(
        "--json-out",
        default="output/diverg_estrutura.json",
        help="Caminho do JSON de saída com as divergências."
    )
    p.add_argument(
        "--sinapi-sheet",
        default="Analítico",
        help="(Opcional) Nome da aba Analítico no SINAPI. Default: 'Analítico'."
    )
    args = p.parse_args()

    print("== Validar estrutura (A=ORÇAMENTO vs B=BASE) ==")
    print(f"A(orc): {args.orc}")
    print(f"B(base): {args.base}  (tipo={args.base_type})")

    # A: estrutura do orçamento (pais + filhos 1º nível), com filtro por banco (se fornecido)
    banco_a = (args.banco_a or "").strip() or None
    A = load_estrutura_orcamento(args.orc, banco=banco_a)

    # B: dependendo do tipo
    if args.base_type == "ORCAMENTO":
        B = load_estrutura_orcamento(args.base)  # sem filtro (é a base inteira)
    elif args.base_type == "SINAPI":
        B = load_estrutura_sinapi_analitico(args.base, sheet_name=args.sinapi_sheet)
    elif args.base_type == "SUDECAP":
        B = load_estrutura_sudecap(args.base)
    else:
        raise SystemExit("[ERRO] base-type não suportado.")

    diverg = comparar_estruturas(A, B)
    print(f"\nDivergências encontradas: {len(diverg)}")

    os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(diverg, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Divergências salvas em {args.json_out}\n")


if __name__ == "__main__":
    main()
