# scripts/test_secid_precos.py
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any, Iterable, Mapping

# se você já exportou PYTHONPATH="$PWD", não precisa deste bloco;
# deixe-o aqui para quem rodar direto sem setar PYTHONPATH.
import sys
ROOT = Path(__file__).resolve().parents[1]  # .../worker
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cruzar_orcamento.adapters.secid import load_secid_precos  # type: ignore

def f(it: Any, name: str, default=None):
    """Obtém campo tanto de dict quanto de objeto (getattr)."""
    if isinstance(it, Mapping):
        return it.get(name, default)
    return getattr(it, name, default)

def pick(it: Any, names: Iterable[str], default=None):
    """Tenta uma lista de possíveis nomes de campo (ex.: valor/preco/custo)."""
    for n in names:
        v = f(it, n, None)
        if v is not None:
            return v
    return default

def main():
    ap = argparse.ArgumentParser(description="Smoke test do loader SECID (preços).")
    ap.add_argument("arquivo", help="Caminho do XLSX/XLS da SECID")
    ap.add_argument("-n", "--num", type=int, default=10, help="Quantos itens exibir")
    args = ap.parse_args()

    path = Path(args.arquivo).expanduser().resolve()
    if not path.exists():
        print(f"Arquivo não encontrado: {path}")
        raise SystemExit(2)

    print(f"Arquivo: {path}")

    items = load_secid_precos(str(path))  # pode ser List[dict] ou Dict[str, dict/obj]
    # Normaliza para um iterável de itens
    if isinstance(items, Mapping):
        seq = list(items.values())
    elif isinstance(items, (list, tuple)):
        seq = list(items)
    else:
        raise TypeError(f"Retorno inesperado de load_secid_precos: {type(items)}")

    print(f"Itens lidos: {len(seq)}")

    # Ordena por código (se existir)
    def code_key(x: Any):
        c = str(f(x, "codigo", "") or f(x, "code", "") or "")
        return c
    seq.sort(key=code_key)

    # Exibe os N primeiros
    N = max(0, args.num)
    for it in seq[:N]:
        codigo     = pick(it, ["codigo", "code", "cod"], "-")
        descricao  = pick(it, ["descricao", "descrição", "desc", "nome"], "-")
        unidade    = pick(it, ["unidade", "und", "uni", "un"], "-")
        valor      = pick(it, ["valor", "preco", "preço", "preco_unitario", "valor_unitario", "custo"], None)
        fonte      = pick(it, ["fonte", "banco", "origem"], "SECID")

        if isinstance(descricao, str) and len(descricao) > 80:
            descricao = descricao[:77] + "..."

        try:
            vtxt = f"{float(valor):.2f}" if valor is not None else "-"
        except Exception:
            vtxt = str(valor) if valor is not None else "-"

        print(f"{str(codigo):>10}  {unidade:<6}  {vtxt:>10}  {fonte:<8}  {descricao}")

if __name__ == "__main__":
    main()
