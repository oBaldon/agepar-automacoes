# scripts/test_cruzamento.py
import os, sys, logging
sys.path.append("src")
from cruzar_orcamento.exporters.excel import export_cruzamento_excel
from cruzar_orcamento.adapters.orcamento import load_orcamento
from cruzar_orcamento.adapters.sudecap import load_sudecap
from cruzar_orcamento.validators.processor import cruzar

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

orc_path = "data/ORÇAMENTO - ACIONAMENTO 01 - REV 05 final.xlsx"
sud_path = "data/2025.04-tabela-de-construcao-desonerada.xlsx"

orc = load_orcamento(orc_path)
sud = load_sudecap(sud_path)

# exemplo: filtrar orçamento por SUDECAP e cruzar com a tabela SUDECAP
cruzado, diverg = cruzar(orc, sud, banco="SUDECAP", tol_rel=0.0)

# depois de calcular cruzado, diverg
print(f"Cruzado: {len(cruzado)} | Divergências: {len(diverg)}\n")

for row in cruzado:
    if row["match"]:
        dif_abs = None
        dif_rel = None
        if row["b_valor"] and row["b_valor"] != 0:
            dif_abs = abs(row["a_valor"] - row["b_valor"])
            dif_rel = dif_abs / row["b_valor"]
        dif_abs_str = f"{dif_abs:.6f}" if dif_abs is not None else "n/a"
        dif_rel_pct_str = f"{dif_rel*100:.4f}%" if dif_rel is not None else "n/a"
        print(
            f"[OK/MATCH] {row['codigo']} | banco={row['a_banco']}\n"
            f"  A(desc): {row['a_desc']}\n"
            f"  B(desc): {row['b_desc']}\n"
            f"  A(valor): {row['a_valor']:.6f} | B(valor): {row['b_valor']:.6f}\n"
            f"  Δabs: {dif_abs_str} | Δrel: {dif_rel_pct_str}\n"
        )
    else:
        print(f"[SEM MATCH] {row['codigo']} | banco={row['a_banco']} | {row['a_desc']}")

if diverg:
    print("Divergências:")
    for d in diverg:
        dif_abs_str = f"{d['dif_abs']:.6f}" if d["dif_abs"] is not None else "n/a"
        dif_rel_pct_str = f"{d['dif_rel']*100:.4f}%" if d["dif_rel"] is not None else "n/a"
        print(f"- {d['codigo']} | motivos={d['motivos']} | Δabs={dif_abs_str} | Δrel={dif_rel_pct_str}")
out_path = export_cruzamento_excel(cruzado, diverg, "output/cruzamento.xlsx")
print(f"Excel gerado em: {out_path}")