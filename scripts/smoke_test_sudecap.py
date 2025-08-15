import os
import logging
from pprint import pprint

# permitir importar de src/
import sys
sys.path.append("src")

from cruzar_orcamento.adapters.orcamento import load_orcamento
from cruzar_orcamento.adapters.sudecap import load_sudecap

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def show_sample(name, data: dict, n=5):
    print(f"\n=== {name} ===")
    print(f"Total de códigos: {len(data)}")
    # pega n primeiros itens
    for i, (cod, item) in enumerate(data.items()):
        if i >= n:
            break
        print(
            f"- {cod}: {item['descricao'][:80]!r} | valor_unit={item['valor_unit']} "
            f"| fonte={item['fonte']}"
            + (f" | banco={item['banco']}" if 'banco' in item else "")
        )
        
def main():
    # ajuste os nomes dos arquivos conforme os seus na pasta data/
    orc_path = os.path.join("data", "ORÇAMENTO - ACIONAMENTO 01 - REV 05 final.xlsx")     # ex.: "ORÇAMENTO - ACIONAMENTO 01 - REV 05 final.xlsx"
    sud_path = os.path.join("data", "2025.04-tabela-de-construcao-desonerada.xlsx")

    # TESTE ORÇAMENTO
    try:
        orc = load_orcamento(orc_path, banco=None)  # se quiser, passe banco="SUDECAP" ou algo do seu arquivo
        show_sample("ORCAMENTO (canônico)", orc)
    except Exception as e:
        print("\n[ERRO] Falha ao carregar ORCAMENTO:", e)

    # TESTE SUDECAP
    try:
        sud = load_sudecap(sud_path)
        show_sample("SUDECAP (canônico)", sud)
    except Exception as e:
        print("\n[ERRO] Falha ao carregar SUDECAP:", e)

if __name__ == "__main__":
    main()
