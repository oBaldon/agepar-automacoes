#!/usr/bin/env python3
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.abspath("src"))

from datetime import date
import argparse

from cruzar_orcamento.fetchers.providers.sinapi import fetch_latest_sinapi_referencia_xlsx

def main():
    p = argparse.ArgumentParser(description="Teste de fetch do SINAPI (extrai Referência .xlsx de dentro do ZIP).")
    p.add_argument("--year", type=int, help="Ano base (default: ano atual)")
    p.add_argument("--month", type=int, help="Mês base 1-12 (default: mês atual)")
    p.add_argument("--back", type=int, default=18, help="Voltar até N meses (default: 18)")
    args = p.parse_args()

    today = date.today()
    base = date(args.year or today.year, args.month or today.month, 1)

    print(f">> Buscando SINAPI (ZIP) a partir de {base:%Y-%m}, back={args.back}…")
    try:
        xlsx_path = fetch_latest_sinapi_referencia_xlsx(base, max_months_back=args.back)
    except Exception as e:
        print(f"[ERRO] {e}")
        sys.exit(2)

    print(f">> OK! Extraído: {xlsx_path}")

if __name__ == "__main__":
    main()
