from __future__ import annotations
import os, time, random, requests, tempfile, shutil

DEFAULT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
    "Connection": "keep-alive",
}

def make_session(headers: dict | None = None) -> requests.Session:
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    if headers:
        s.headers.update(headers)
    return s

def warmup(session: requests.Session, url_root: str, timeout: float = 15.0) -> None:
    # tenta abrir a pasta-base para setar cookie da GoCache
    try:
        session.get(url_root, allow_redirects=True, timeout=timeout)
    except requests.RequestException:
        pass

def head_ok(url: str, timeout: float = 15.0, headers: dict | None = None,
            session: requests.Session | None = None) -> bool:
    sess = session or make_session(headers)
    try:
        r = sess.head(url, allow_redirects=True, timeout=timeout)
        return 200 <= r.status_code < 300
    except requests.RequestException:
        return False

def url_exists(url: str, timeout: float = 15.0, headers: dict | None = None,
               session: requests.Session | None = None) -> bool:
    """
    1) HEAD
    2) GET leve (stream). Se vier HTML (provável bloqueio da GoCache), retornamos False
       para forçar o loop a continuar tentando meses anteriores.
    """
    sess = session or make_session(headers)

    # 1) HEAD
    try:
        r = sess.head(url, allow_redirects=True, timeout=timeout)
        if 200 <= r.status_code < 300:
            return True
    except requests.RequestException:
        pass

    # 2) GET leve
    try:
        with sess.get(url, stream=True, allow_redirects=True, timeout=timeout) as r:
            if not (200 <= r.status_code < 300):
                return False
            ct = (r.headers.get("Content-Type") or "").lower()
            if "text/html" in ct:
                return False
            for chunk in r.iter_content(1024):
                if chunk:
                    return True
            return False
    except requests.RequestException:
        return False

def download_file(url: str, dest_path: str, timeout: float = 120.0,
                  retries: int = 4, backoff: float = 1.6, min_bytes: int = 1024,
                  headers: dict | None = None,
                  session: requests.Session | None = None,
                  debug_name: str | None = None) -> None:
    """
    Baixa com retries usando sessão. Se receber HTML (bloqueio),
    salva uma amostra em data/_debug_*.html para diagnóstico.
    """
    last = None
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    sess = session or make_session(headers)

    for attempt in range(retries):
        try:
            with sess.get(url, stream=True, allow_redirects=True, timeout=timeout) as r:
                r.raise_for_status()
                ct = (r.headers.get("Content-Type") or "").lower()

                # bloqueio da GoCache: HTML
                if "text/html" in ct:
                    # salva corpo para debug
                    try:
                        body = r.content[:4096]
                        dbg_dir = os.path.join(os.path.dirname(dest_path) or ".", "")
                        os.makedirs(dbg_dir, exist_ok=True)
                        dbg_name = debug_name or "debug_fetch.html"
                        with open(os.path.join("data", f"_{dbg_name}"), "wb") as f:
                            f.write(body)
                    except Exception:
                        pass
                    raise RuntimeError(f"Resposta HTML inesperada (status {r.status_code})")

                # grava com tmp + rename
                with tempfile.NamedTemporaryFile("wb", delete=False,
                                                 dir=os.path.dirname(dest_path) or ".") as tmp:
                    tmp_path = tmp.name
                    total = 0
                    for chunk in r.iter_content(262_144):
                        if not chunk:
                            continue
                        tmp.write(chunk)
                        total += len(chunk)

                if total < min_bytes:
                    raise RuntimeError(f"Arquivo muito pequeno ({total} bytes)")

                os.replace(tmp_path, dest_path)
                return

        except Exception as e:
            last = e
            sleep_s = (backoff ** attempt) + random.uniform(0, 0.5)
            time.sleep(sleep_s)
            try:
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    raise RuntimeError(f"Falha ao baixar {url}: {last}")
