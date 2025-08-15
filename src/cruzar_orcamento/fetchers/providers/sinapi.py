# src/cruzar_orcamento/fetchers/providers/sinapi.py
from __future__ import annotations

import os
import shutil
import tempfile
import unicodedata
from datetime import date
from typing import Tuple
from zipfile import ZipFile

import requests

from ..base import _fmt_file
from ..http import download_file

_BASE = "https://www.caixa.gov.br/Downloads/sinapi-relatorios-mensais"

def _strip_accents(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()

def sinapi_zip_url_builder(d: date) -> str:
    # Ex.: SINAPI-2025-06-formato-xlsx.zip
    return f"{_BASE}/SINAPI-{d.year:04d}-{d.month:02d}-formato-xlsx.zip"

# Nome interno esperado dentro do ZIP (vem com acento)
def _wanted_inner_name(d: date) -> str:
    return f"SINAPI_Referência_{d.year:04d}_{d.month:02d}.xlsx"

def _matches_target(member_name: str, target: str) -> bool:
    m_base = os.path.basename(member_name)
    if m_base == target:
        return True
    return _strip_accents(m_base) == _strip_accents(target)

HEADERS_SINAPI = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
    "Connection": "keep-alive",
    # referer da própria página de downloads da Caixa ajuda a evitar HTML/portal
    "Referer": "https://www.caixa.gov.br/Downloads/sinapi-relatorios-mensais/",
}

def _dec_month(d: date, n: int) -> date:
    y, m = d.year, d.month
    m -= n
    while m <= 0:
        y -= 1
        m += 12
    return date(y, m, 1)

def _quick_response_log(path: str, url: str, resp: requests.Response, sample_bytes: int = 1024) -> None:
    """Grava status, headers e primeiros bytes da resposta para depuração rápida."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    body_preview = b""
    try:
        for chunk in resp.iter_content(sample_bytes):
            if chunk:
                body_preview = chunk[:sample_bytes]
                break
    except Exception:
        pass

    try:
        text_preview = body_preview.decode(resp.encoding or "utf-8", errors="replace")
    except Exception:
        text_preview = repr(body_preview)

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write(f"Final URL (after redirects): {getattr(resp, 'url', url)}\n")
        f.write(f"Status: {resp.status_code}\n")
        f.write("Response headers:\n")
        for k, v in resp.headers.items():
            f.write(f"  {k}: {v}\n")
        f.write(f"\n--- Body preview (first ~{sample_bytes} bytes) ---\n")
        f.write(text_preview)
        f.write("\n")

def _exists_file_like_zip(url: str, debug_log_path: str | None, timeout: float = 25.0) -> Tuple[bool, str]:
    """
    Verifica se a URL parece um ZIP “real” (não HTML).
    Considera sucesso para 200–299 com Content-Type não-HTML e ao menos um chunk.
    Em falha, grava log curto.
    Retorna (ok, content_type).
    """
    try:
        with requests.get(url, headers=HEADERS_SINAPI, stream=True, allow_redirects=True, timeout=timeout) as r:
            ct = (r.headers.get("Content-Type") or "").lower()
            ok_status = 200 <= r.status_code < 300
            if ok_status and "text/html" not in ct:
                # tenta ler 1 bloco
                for chunk in r.iter_content(1024):
                    if chunk:
                        return True, ct
                if debug_log_path:
                    _quick_response_log(debug_log_path, url, r)
                return False, ct
            else:
                if debug_log_path:
                    _quick_response_log(debug_log_path, url, r)
                return False, ct
    except requests.RequestException:
        if debug_log_path:
            try:
                with open(debug_log_path, "w", encoding="utf-8") as f:
                    f.write(f"URL: {url}\nNetwork error while probing.\n")
            except Exception:
                pass
        return False, ""

def find_latest_sinapi(start: date, max_months_back: int = 36, *, debug_log: bool = True) -> tuple[date, str]:
    """
    Retrocede mês a mês montando a URL do ZIP. Faz GET leve para checar existência real.
    Se falhar, grava logs em data/_debug_sinapi_YYYY_MM.log.
    """
    out_dir = "data"
    for back in range(max_months_back + 1):
        d = _dec_month(start, back)
        url = sinapi_zip_url_builder(d)
        print(f"[DEBUG] Tentando: {d:%Y-%m} -> {url}")
        log_path = os.path.join(out_dir, f"_debug_sinapi_{d.year:04d}_{d.month:02d}.log") if debug_log else None
        ok, ct = _exists_file_like_zip(url, debug_log_path=log_path)

        if ok:
            # remove log se existir
            if log_path and os.path.exists(log_path):
                try:
                    os.remove(log_path)
                except Exception:
                    pass
            print(f"[DEBUG] OK: encontrado {d:%Y-%m} (ct={ct or 'unknown'})")
            return d, url

        suffix = os.path.basename(log_path) if log_path else "no-log"
        print(f"[DEBUG] não encontrado: {d:%Y-%m} ({suffix})")

    raise RuntimeError(f"Nenhuma versão encontrada para SINAPI-ZIP nos últimos {max_months_back} meses.")

def fetch_latest_sinapi_referencia_xlsx(start: date, max_months_back: int = 36, *, debug_log: bool = True) -> str:
    """
    Busca retroativamente o ZIP do SINAPI e extrai apenas o
    'SINAPI_Referência_{YYYY}_{MM}.xlsx' para a pasta 'data/' com nome:
        data/SINAPI_{YYYY}_{MM}.xlsx
    Retorna o caminho do .xlsx extraído.
    """
    d, url = find_latest_sinapi(start, max_months_back=max_months_back, debug_log=debug_log)

    out_dir = "data"
    os.makedirs(out_dir, exist_ok=True)

    # Baixa o ZIP para temp
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_zip = os.path.join(tmpdir, _fmt_file("SINAPI_{YYYY}_{MM}.zip", d))
        # usa headers da Caixa
        download_file(url, tmp_zip, headers=HEADERS_SINAPI)

        # Abre e acha o arquivo alvo interno
        target_name = _wanted_inner_name(d)
        with ZipFile(tmp_zip, "r") as zf:
            candidate = next((n for n in zf.namelist() if _matches_target(n, target_name)), None)
            if candidate is None:
                listing = "\n".join(zf.namelist()[:40])
                raise RuntimeError(
                    f"Arquivo alvo '{target_name}' não encontrado no ZIP.\n"
                    f"Alguns arquivos no ZIP:\n{listing}"
                )

            # Extrai com nome padronizado sem “Referência”
            dest_name = f"SINAPI_{d.year:04d}_{d.month:02d}.xlsx"
            dest_path = os.path.join(out_dir, dest_name)
            with zf.open(candidate) as src, open(dest_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

    return dest_path
