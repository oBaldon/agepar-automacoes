#!/usr/bin/env python3
from __future__ import annotations

import sys
import os
from datetime import date
import argparse

# Permitir imports relativos ao projeto
sys.path.insert(0, os.path.abspath("src"))

# Importa funções específicas do SUDECAP
from cruzar_orcamento.fetchers.providers.sudecap import (
    find_latest_sudecap,
    fetch_latest_sudecap,
)

def main():
    parser = argparse.ArgumentParser(
        description="Teste de fetch para SUDECAP (busca retroativa e por ano)."
    )
    parser.add_argument(
        "--mode",
        choices=["retro", "year"],
        default="retro",
        help="retro: busca voltando meses até achar; year: encontra o último daquele ano.",
    )
    parser.add_argument("--year", type=int, help="Ano base/alvo. retro: base; year: ano alvo.")
    parser.add_argument("--month", type=int, help="Mês base (1-12), apenas no modo retro.")
    parser.add_argument(
        "--back",
        type=int,
        default=24,
        help="retro: voltar até N meses (padrão: 24).",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="data",
        help="Diretório onde salvar o arquivo baixado.",
    )
    args = parser.parse_args()

    today = date.today()

    if args.mode == "retro":
        base = date(args.year or today.year, args.month or today.month, 1)
        print(f">> [RETRO] Buscando SUDECAP a partir de {base:%Y-%m} (back={args.back})…")
        try:
            dest = fetch_latest_sudecap(
                base,
                max_months_back=args.back,
                out_dir=args.out_dir,
            )
        except Exception as e:
            print(f"[ERRO] {e}", file=sys.stderr)
            sys.exit(2)
        print(f">> OK: baixado em {dest}")

    elif args.mode == "year":
        if not args.year:
            print("[ERRO] --year é obrigatório no modo 'year'", file=sys.stderr)
            sys.exit(2)

        # Busca do mês 12 até o 1 do ano informado
        start = date(args.year, 12, 1)
        print(f">> [YEAR] Buscando a última versão de SUDECAP em {args.year}…")
        try:
            d, url = find_latest_sudecap(
                start,
                max_months_back=11,
            )
        except Exception as e:
            print(f"[ERRO] {e}", file=sys.stderr)
            sys.exit(2)

        print(f">> Encontrado: {d:%Y-%m} | URL: {url}")
        try:
            dest = fetch_latest_sudecap(
                d,
                max_months_back=0,
                out_dir=args.out_dir,
            )
        except Exception as e:
            print(f"[ERRO] Falha ao baixar {url}: {e}", file=sys.stderr)
            sys.exit(3)
        print(f">> OK: baixado em {dest}")

if __name__ == "__main__":
    main()
