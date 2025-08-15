#!/usr/bin/env python3
from __future__ import annotations

import sys
import os
import json
import argparse
import logging
from itertools import islice

# permitir "python scripts/..." sem instalar o pacote
sys.path.insert(0, os.path.abspath("src"))

from cruzar_orcamento.adapters.estrutura_orcamento import load_estrutura_orcamento  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke test: extrai estrutura (pai + filhos de 1º nível) do ORÇAMENTO."
    )
    parser.add_argument(
        "--orc",
        required=True,
        help="Caminho do Excel do orçamento (aba(s) de 'Composições').",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Quantos pais mostrar no preview (padrão: 5).",
    )
    parser.add_argument(
        "--code",
        default="",
        help="Se informado, mostra somente a composição mestra desse código.",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Se informado, salva a estrutura completa em JSON neste caminho.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nível de log (padrão: INFO).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")

    print("== Testando estrutura do ORÇAMENTO ==")
    print(f"Arquivo: {args.orc}")

    estrutura = load_estrutura_orcamento(args.orc)

    total_pais = len(estrutura)
    total_filhos = sum(len(v["filhos"]) for v in estrutura.values())
    print()
    print(f"Total de composições (pais): {total_pais}")
    print(f"Total de filhos (1º nível): {total_filhos}")

    # Filtro por código (se solicitado)
    if args.code:
        comp = estrutura.get(args.code)
        if not comp:
            print(f"\n[CÓDIGO] '{args.code}' não encontrado na estrutura.")
            sys.exit(1)
        comps_iter = [(args.code, comp)]
        header = f"\nPreview somente de '{args.code}':"
    else:
        comps_iter = islice(estrutura.items(), args.limit)
        header = f"\nPreview dos primeiros {min(args.limit, total_pais)} pais:"

    print(header)
    for i, (cod, comp) in enumerate(comps_iter, 1):
        pai_desc = comp["descricao"]
        filhos = comp["filhos"]
        print(f"\n[{i}] PAI {cod} — {pai_desc}")
        if not filhos:
            print("   (sem filhos)")
        else:
            for j, f in enumerate(filhos, 1):
                print(f"   - filho #{j}: {f['codigo']} — {f['descricao']}")

    # Dump JSON (opcional)
    if args.json_out:
        try:
            # json serializável diretamente (todos são str/list/dict)
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(estrutura, f, ensure_ascii=False, indent=2)
            print(f"\n[OK] Estrutura salva em JSON → {args.json_out}")
        except Exception as e:
            print(f"\n[ERRO] Falha ao salvar JSON: {e}")
            sys.exit(2)

    print("\nOK ✅")


if __name__ == "__main__":
    main()
