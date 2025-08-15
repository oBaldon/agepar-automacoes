# 1) Preço (manual) — SINAPI
python -m src.cli run-precos \
  --orc "data/ORÇAMENTO - ACIONAMENTO 01 - REV 05 final.xlsx" \
  --ref "data/SINAPI_2025_06.xlsx" \
  --ref-type SINAPI \
  --banco SINAPI \
  --tol-rel 0.00 \
  --out output/cruzamento_precos_sinapi.json

# 2) Preço (manual) — SUDECAP
python -m src.cli run-precos \
  --orc "data/ORÇAMENTO - ACIONAMENTO 01 - REV 05 final.xlsx" \
  --ref "data/SUDECAP_2025_04.xls" \
  --ref-type SUDECAP \
  --banco SUDECAP \
  --tol-rel 0.00 \
  --out output/cruzamento_precos_sudecap.json

# 3) Preço (automático) — usa últimos arquivos em data/
python -m src.cli run-precos-auto \
  --orc "data/ORÇAMENTO - ACIONAMENTO 01 - REV 05 final.xlsx" \
  --tol-rel 0.00 \
  --out-dir output

# 4) Estrutura — ORÇAMENTO (pais do banco SINAPI) vs SINAPI (Analítico)
python -m src.cli validar-estrutura \
  --orc "data/ORÇAMENTO - ACIONAMENTO 01 - REV 05 final.xlsx" \
  --banco-a SINAPI \
  --base "data/SINAPI_2025_06.xlsx" \
  --base-type SINAPI \
  --out output/diverg_estrutura_sinapi.json

# 5) Estrutura — ORÇAMENTO (pais do banco SUDECAP) vs SUDECAP (Relatório)
python -m src.cli validar-estrutura \
  --orc "data/ORÇAMENTO - ACIONAMENTO 01 - REV 05 final.xlsx" \
  --banco-a SUDECAP \
  --base "data/SUDECAP_COMPOSIÇÕES_2025_04.xls" \
  --base-type SUDECAP \
  --out output/diverg_estrutura_sudecap.json
