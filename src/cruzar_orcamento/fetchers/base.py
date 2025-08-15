# src/cruzar_orcamento/fetchers/base.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Callable, Tuple
import os
from .http import url_exists, download_file  # <— usar url_exists

DateBuilder = Callable[[date], str]

@dataclass
class FetchPlan:
    name: str
    url_builder: DateBuilder
    file_pattern: str
    out_dir: str

def _dec_month(d: date, n: int) -> date:
    y, m = d.year, d.month
    m -= n
    while m <= 0:
        y -= 1
        m += 12
    return date(y, m, 1)

def _fmt_file(pattern: str, d: date) -> str:
    return (pattern.replace("{YYYY}", f"{d.year:04d}")
                   .replace("{YY}", f"{d.year%100:02d}")
                   .replace("{MM}", f"{d.month:02d}"))

def find_latest_available(plan: FetchPlan, start: date, max_months_back: int = 36) -> Tuple[date, str]:
    for back in range(max_months_back + 1):
        d = _dec_month(start, back)
        url = plan.url_builder(d)
        print(f"[DEBUG] Tentando: {d:%Y-%m} -> {url}")  # log de cada tentativa
        if url_exists(url):
            print(f"[DEBUG] OK: encontrado {d:%Y-%m}")
            return d, url
        else:
            print(f"[DEBUG] não encontrado: {d:%Y-%m}")
    raise RuntimeError(f"Nenhuma versão encontrada para {plan.name} nos últimos {max_months_back} meses.")

def fetch_latest(plan: FetchPlan, start: date, max_months_back: int = 36) -> str:
    d, url = find_latest_available(plan, start, max_months_back)
    os.makedirs(plan.out_dir, exist_ok=True)
    dest = os.path.join(plan.out_dir, _fmt_file(plan.file_pattern, d))
    download_file(url, dest)
    return dest
