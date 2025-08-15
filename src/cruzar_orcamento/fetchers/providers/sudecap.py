# src/cruzar_orcamento/fetchers/providers/sudecap.py
from __future__ import annotations

import os
from datetime import date
from typing import Tuple

import requests

from ..base import FetchPlan, _fmt_file
from ..http import download_file

_BASE = ("https://prefeitura.pbh.gov.br/sites/default/files/"
         "estrutura-de-governo/obras-e-infraestrutura")

# Formato fixo exigido
def sudecap_url_builder(d: date) -> str:
    # Ex.: 2025.04-tabela-de-construcao-desonerada.xls
    return f"{_BASE}/{d.year:04d}.{d.month:02d}-tabela-de-construcao-desonerada.xls"

SUDECAP_PLAN = FetchPlan(
    name="SUDECAP",
    url_builder=sudecap_url_builder,
    file_pattern="SUDECAP_{YYYY}_{MM}.xls",
    out_dir="data",
)

HEADERS_SUDECAP = {
    # headers “neutros”, com referer da própria PBH (alguns servidores exigem)
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
    "Connection": "keep-alive",
    "Referer": "https://prefeitura.pbh.gov.br/obras-e-infraestrutura",
}

def _dec_month(d: date, n: int) -> date:
    y, m = d.year, d.month
    m -= n
    while m <= 0:
        y -= 1
        m += 12
    return date(y, m, 1)

def _quick_response_log(path: str, url: str, resp: requests.Response, sample_bytes: int = 1024) -> None:
    """
    Escreve um log curto com status, headers e primeiros bytes do corpo para
    diagnóstico rápido. O arquivo pode ser apagado depois.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    body_preview = b""
    try:
        # Tenta ler só um pedacinho sem consumir tudo
        for chunk in resp.iter_content(sample_bytes):
            if chunk:
                body_preview = chunk[:sample_bytes]
                break
    except Exception:
        pass

    # decodifica em texto (melhor esforço)
    try:
        text_preview = body_preview.decode(resp.encoding or "utf-8", errors="replace")
    except Exception:
        text_preview = repr(body_preview)

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write(f"Final URL (after redirects): {resp.url}\n")
        f.write(f"Status: {resp.status_code}\n")
        f.write("Response headers:\n")
        for k, v in resp.headers.items():
            f.write(f"  {k}: {v}\n")
        f.write("\n--- Body preview (first ~{sample_bytes} bytes) ---\n")
        f.write(text_preview)
        f.write("\n")

def _exists_file_like(url: str, debug_log_path: str | None = None, timeout: float = 20.0) -> Tuple[bool, str]:
    """
    Checagem “real” via GET com stream, sem HEAD/Range.
    Considera existente se status 200–299, não for text/html e houver ao menos um chunk.
    Em caso de falha, grava um log rápido (se debug_log_path for fornecido).
    Retorna (ok, content_type).
    """
    try:
        with requests.get(url, headers=HEADERS_SUDECAP, stream=True, allow_redirects=True, timeout=timeout) as r:
            ct = (r.headers.get("Content-Type") or "").lower()
            ok_status = 200 <= r.status_code < 300
            if ok_status:
                # se parecer HTML, tratamos como “não é arquivo”
                if "text/html" in ct:
                    if debug_log_path:
                        _quick_response_log(debug_log_path, url, r)
                    return (False, ct)
                # tenta ler 1 bloco de dados
                for chunk in r.iter_content(1024):
                    if chunk:
                        return (True, ct)
                # sem bytes => falha
                if debug_log_path:
                    _quick_response_log(debug_log_path, url, r)
                return (False, ct)
            else:
                if debug_log_path:
                    _quick_response_log(debug_log_path, url, r)
                return (False, ct)
    except requests.RequestException:
        # erro de rede: registra algo mínimo
        if debug_log_path:
            try:
                with open(debug_log_path, "w", encoding="utf-8") as f:
                    f.write(f"URL: {url}\n")
                    f.write("Network error while probing.\n")
            except Exception:
                pass
        return (False, "")

def find_latest_sudecap(start: date, max_months_back: int = 24) -> tuple[date, str]:
    """
    Retrocede mês a mês, montando APENAS a URL no formato fixo exigido.
    Para cada tentativa, faz um GET curto e:
      - se não for HTML e tiver bytes, considera encontrado;
      - senão, grava um log rápido em data/_debug_sudecap_YYYY_MM.log e tenta mês anterior.
    """
    for back in range(max_months_back + 1):
        d = _dec_month(start, back)
        url = sudecap_url_builder(d)
        print(f"[DEBUG] Tentando: {d:%Y-%m} -> {url}")

        debug_log = os.path.join(SUDECAP_PLAN.out_dir, f"_debug_sudecap_{d.year:04d}_{d.month:02d}.log")
        ok, ct = _exists_file_like(url, debug_log_path=debug_log)

        if ok:
            # sucesso: podemos remover o log de diagnóstico, se ele existir
            try:
                if os.path.exists(debug_log):
                    os.remove(debug_log)
            except Exception:
                pass
            print(f"[DEBUG] OK: encontrado {d:%Y-%m} (ct={ct or 'unknown'})")
            return d, url

        print(f"[DEBUG] não encontrado: {d:%Y-%m} ({os.path.basename(debug_log)})")

    raise RuntimeError(f"Nenhuma versão encontrada para {SUDECAP_PLAN.name} nos últimos {max_months_back} meses.")

def fetch_latest_sudecap(start: date, max_months_back: int = 24, out_dir: str = "data") -> str:
    """
    Encontra a versão mais recente via find_latest_sudecap e baixa o arquivo
    para data/SUDECAP_YYYY_MM.xls (ou .xlsx se o servidor mudar o tipo).
    """
    d, url = find_latest_sudecap(start, max_months_back=max_months_back)
    os.makedirs(out_dir, exist_ok=True)

    # deduz extensão pelo final da URL (continua .xls como padrão)
    ext = ".xlsx" if url.lower().endswith(".xlsx") else ".xls"
    dest = os.path.join(out_dir, _fmt_file(SUDECAP_PLAN.file_pattern, d).replace(".xls", ext))

    # baixa de fato com os headers da PBH
    download_file(url, dest_path=dest, headers=HEADERS_SUDECAP)
    return dest
