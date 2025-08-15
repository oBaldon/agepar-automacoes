#!/usr/bin/env python3
import sys, logging, traceback
from pathlib import Path

# permitir "python scripts/..." sem instalar o pacote
sys.path.append("src")

from cruzar_orcamento.adapters.sinapi import load_sinapi_ccd_pr

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    # ajuste o caminho se necessário
    ref_path = Path("data/SINAPI_Referência_2025_06.xlsx")

    if not ref_path.exists():
        print(f"[ERRO] Arquivo não encontrado: {ref_path}")
        sys.exit(1)

    print(f"== Testando SINAPI CCD (PR) ==")
    print(f"Arquivo: {ref_path}")

    try:
        ref_dict = load_sinapi_ccd_pr(str(ref_path), cidade="CURITIBA")
    except Exception as e:
        print("\n[ERRO] Falha no adapter SINAPI CCD PR:\n")
        traceback.print_exc()
        print("\nDicas:")
        print("- Verifique se a aba 'CCD' existe e se tem as colunas do PR (CURITIBA).")
        print("- Se o erro citar 'coluna Código', pode ser por cabeçalho mesclado; me avise que mando patch.")
        sys.exit(2)

    print(f"\nTotal de códigos carregados: {len(ref_dict)}")
    # Amostra
    sample = list(ref_dict.items())[:10]
    for cod, item in sample:
        print(f"- {cod}: {item['descricao'][:80]!r} | valor_unit={item['valor_unit']} | fonte={item['fonte']}")

    # Verifica se há códigos em branco (não deveria)
    blanks = [c for c, it in ref_dict.items() if not c or str(c).strip() == ""]
    if blanks:
        print(f"\n[AVISO] {len(blanks)} código(s) em branco detectado(s).")

    print("\nOK ✅")

if __name__ == "__main__":
    main()
