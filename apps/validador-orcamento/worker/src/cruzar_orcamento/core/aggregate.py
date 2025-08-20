# src/cruzar_orcamento/core/aggregate.py
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..utils.utils_code import norm_code_canonical
from ..utils.utils_text import norm_text


# ============================================================
# Helpers
# ============================================================

_OCC_RE = re.compile(r"__occ\d+$", re.IGNORECASE)


def _canon(code: Any) -> str:
    """
    Canoniza códigos para match entre Orçamento e bases de referência.

    - Remove sufixos de ocorrência do Orçamento (ex.: "__occ1", "__occ2", ...).
    - Aplica `norm_code_canonical` (remove ".0", zeros à esquerda por segmento etc.).

    Retorna string vazia quando `code` é None.
    """
    if code is None:
        return ""
    s = str(code).strip()
    s = _OCC_RE.sub("", s)
    return norm_code_canonical(s)

"""def _canon(code: Any) -> str:
    Canoniza códigos respeitando o formato esperado:

    - Remove sufixos de ocorrência "__occN".
    - Aplica norm_code_canonical para normalização geral.
    - Regras especiais para o ÚLTIMO segmento (apenas ele):
        * Se o último segmento original começava com '0', garanta largura de 2 dígitos.
        * Remova zeros à direita do último segmento somente até restarem 2 dígitos.

    Exemplos:
        "01.12.01"   -> "1.12.01"
        "41.31.070"  -> "41.31.07"
    if code is None:
        return ""
    raw = str(code).strip()
    raw = _OCC_RE.sub("", raw)

    raw_parts = raw.split(".")
    raw_last = raw_parts[-1] if raw_parts else ""

    base = norm_code_canonical(raw)  # mantém compatibilidade com adapters
    parts = base.split(".")

    if parts:
        if raw_last.startswith("0"):
            last = parts[-1]
            # corta zeros à direita até ficar com 2 dígitos no mínimo
            while len(last) > 2 and last.endswith("0"):
                last = last[:-1]
            # se sobrar 1 dígito, preenche à esquerda
            if len(last) < 2:
                last = last.zfill(2)
            parts[-1] = last

    return ".".join(parts)
"""


def _to_float(x: Any) -> Optional[float]:
    """
    Converte valores heterogêneos para float.

    - Aceita int/float diretamente.
    - Converte strings trocando vírgula por ponto.
    - Retorna None em branco/None/conversão inválida.
    """
    if x is None or x == "":
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _dir(a_val: Optional[float], b_val: Optional[float]) -> str:
    """
    Direção da divergência considerando A=Orçamento e B=Referência.

    Retorna:
      - "MAIOR"  se A > B
      - "MENOR"  se A < B
      - "IGUAL"  se A == B
      - ""       se não há valores comparáveis
    """
    if a_val is None or b_val is None:
        return ""
    if a_val > b_val:
        return "MAIOR"
    if a_val < b_val:
        return "MENOR"
    return "IGUAL"


def _bank_norm(banco: Any) -> Optional[str]:
    """
    Normaliza o campo 'banco' do item do Orçamento para as bases suportadas.

    - Retorna "SINAPI" se contiver "sinapi" (case-insensitive).
    - Retorna "SUDECAP" se contiver "sudecap".
    - Retorna None para bancos não suportados ou ausentes (ex.: "SBC", "CPOS/CDHU", "").
    """
    if not banco:
        return None
    s = str(banco).strip().casefold()
    if "sinapi" in s:
        return "SINAPI"
    if "sudecap" in s:
        return "SUDECAP"
    return None  # SBC, CPOS/CDHU, etc.


# ============================================================
# PREÇOS
# ============================================================

def _compare_precos(
    a_desc: str,
    a_val: Optional[float],
    b_desc: Optional[str],
    b_val: Optional[float],
    tol_rel: float,
    comparar_descricao: bool,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Compara um item do Orçamento (a_desc/a_val) com o item da base (b_desc/b_val).

    Regras:
      - "OK" (True) somente se existir item na base e:
          • preço dentro da tolerância relativa (ou ambas as bases com 0/None), e
          • (se habilitado) descrição equivalente via `norm_text`.
      - Divergências retornam `False` e um dict `extras` contendo:
          • motivos: lista[str] (ex.: "CODIGO_NAO_ENCONTRADO", "VALOR_DIVERGENTE", "DESCRICAO_DIVERGENTE", ...),
          • dif_abs/dif_rel/dir quando aplicável,
          • a_desc/b_desc quando houver divergência de descrição.

    Observação:
      - Mesmo quando o preço de referência for 0/None, a descrição ainda é verificada.
    """
    motivos: List[str] = []
    extras: Dict[str, Any] = {}

    # 1) código não encontrado na base
    if b_desc is None and b_val is None:
        motivos.append("CODIGO_NAO_ENCONTRADO")
    else:
        # 2) preço
        a = _to_float(a_val)
        b = _to_float(b_val)

        if b is None or b == 0:
            # Base ausente/zero: considera divergente se valores diferirem
            if (a or 0.0) != (b or 0.0):
                motivos.append("VALOR_BASE_ZERO_OU_NULO")
                extras["dir"] = _dir(a, b or 0.0)
        else:
            if a is None:
                motivos.append("VALOR_ORCAMENTO_NULO")
            else:
                dif_abs = abs(a - b)
                dif_rel = dif_abs / b
                if dif_rel > tol_rel:
                    motivos.append("VALOR_DIVERGENTE")
                    extras["dif_abs"] = dif_abs
                    extras["dif_rel"] = dif_rel
                    extras["dir"] = _dir(a, b)

    # 3) descrição (só se habilitado; compara sempre que há alguma referência)
    if comparar_descricao:
        if norm_text(a_desc) != norm_text(b_desc or ""):
            motivos.append("DESCRICAO_DIVERGENTE")
            extras["a_desc"] = a_desc
            if b_desc is not None:
                extras["b_desc"] = b_desc

    # 4) resultado
    if motivos:
        extras["motivos"] = motivos
        return False, extras

    return True, extras


def _build_ref_block(
    a_desc: str,
    a_val: Optional[float],
    ref_item: Optional[Dict[str, Any]],
    tol_rel: float,
    comparar_descricao: bool,
) -> Dict[str, Any]:
    """
    Monta o bloco de comparação para uma referência (SINAPI/SUDECAP).

    Retorna:
      { "valor": <float|None>, "ok": <bool> }  # sempre
    e, quando ok=False, inclui também:
      "motivos", "dif_abs", "dif_rel", "dir", "a_desc", "b_desc" (quando existirem).
    """
    b_desc = ref_item.get("descricao") if ref_item else None
    b_val = ref_item.get("valor_unit") if ref_item else None
    ok, extras = _compare_precos(a_desc, a_val, b_desc, b_val, tol_rel, comparar_descricao)
    out: Dict[str, Any] = {"valor": b_val, "ok": ok}
    if not ok:
        # entram motivos/dif_abs/dif_rel/dir e a_desc/b_desc (se aplicável)
        out.update(extras)
    return out


def consolidar_precos(
    orc: Dict[str, Dict[str, Any]],
    sinapi: Dict[str, Dict[str, Any]],
    sudecap: Dict[str, Dict[str, Any]],
    *,
    tol_rel: float = 0.05,
    comparar_descricao: bool = True,
) -> Dict[str, Any]:
    """
    Consolida ORÇAMENTO vs (SINAPI/SUDECAP) em um único payload.

    Política de comparação:
      - Cada item do Orçamento é comparado APENAS com a base indicada pelo seu 'banco'.
        • banco ≈ "SINAPI"  -> compara com SINAPI; SUDECAP fica {"nao_aplicavel": true}
        • banco ≈ "SUDECAP" -> compara com SUDECAP; SINAPI  fica {"nao_aplicavel": true}
        • bancos ausentes/não suportados -> ambos "nao_aplicavel"
      - O match usa código canônico (remove __occN e normaliza formato).

    Saída:
      - meta/resumo,
      - "cruzado": itens com campos do orçamento + blocos "sinapi"/"sudecap",
      - "divergencias": somente entradas efetivamente comparadas e com ok=False.
    """
    itens: List[Dict[str, Any]] = []
    sinapi_ok = sudecap_ok = 0
    sinapi_comp = sudecap_comp = 0
    ignorados_por_banco = 0

    for key, a in orc.items():
        codigo_orc = a.get("codigo") or key
        codigo_base = _canon(codigo_orc)

        a_desc = a.get("descricao", "")
        a_val = _to_float(a.get("valor_unit"))
        a_banco = _bank_norm(a.get("banco"))

        # busca nas bases pelo código canônico (fallback para formas brutas, por segurança)
        s = sinapi.get(codigo_base) or sinapi.get(codigo_orc) or sinapi.get(key)
        u = sudecap.get(codigo_base) or sudecap.get(codigo_orc) or sudecap.get(key)

        if a_banco == "SINAPI":
            sinapi_comp += 1
            sin_block = _build_ref_block(a_desc, a_val, s, tol_rel, comparar_descricao)
            sud_block = {"nao_aplicavel": True}
            if sin_block.get("ok"):
                sinapi_ok += 1

        elif a_banco == "SUDECAP":
            sudecap_comp += 1
            sud_block = _build_ref_block(a_desc, a_val, u, tol_rel, comparar_descricao)
            sin_block = {"nao_aplicavel": True}
            if sud_block.get("ok"):
                sudecap_ok += 1

        else:
            # banco ausente ou não suportado deve ser ignorado (sem gerar falsos negativos)
            ignorados_por_banco += 1
            sin_block = {"nao_aplicavel": True}
            sud_block = {"nao_aplicavel": True}

        itens.append({
            "codigo": str(codigo_orc),
            "codigo_base": codigo_base,   # útil para diagnóstico e ordenação estável
            "a_banco": a.get("banco"),
            "a_desc": a_desc,
            "a_valor": a_val,
            "sinapi": sin_block,
            "sudecap": sud_block,
        })

    # Divergências: somente onde houve comparação (não 'nao_aplicavel') e ok=False
    divergencias: List[Dict[str, Any]] = []
    for it in itens:
        # SINAPI
        sb = it["sinapi"]
        if not sb.get("nao_aplicavel") and not sb.get("ok"):
            d = {"ref": "SINAPI", "codigo": it["codigo_base"]}
            for k in ("motivos", "dif_abs", "dif_rel", "dir", "a_desc", "b_desc"):
                v = sb.get(k)
                if v is not None:
                    d[k] = v
            divergencias.append(d)
        # SUDECAP
        ub = it["sudecap"]
        if not ub.get("nao_aplicavel") and not ub.get("ok"):
            d = {"ref": "SUDECAP", "codigo": it["codigo_base"]}
            for k in ("motivos", "dif_abs", "dif_rel", "dir", "a_desc", "b_desc"):
                v = ub.get(k)
                if v is not None:
                    d[k] = v
            divergencias.append(d)

    payload: Dict[str, Any] = {
        "meta": {
            "tol_rel": tol_rel,
            "comparar_descricao": comparar_descricao,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
        "resumo": {
            "itens_orc": len(itens),
            "comparados": {"sinapi": sinapi_comp, "sudecap": sudecap_comp},
            "ok": {"sinapi_ok": sinapi_ok, "sudecap_ok": sudecap_ok},
            "ignorados_por_banco": ignorados_por_banco,
        },
        "cruzado": sorted(itens, key=lambda r: (r["codigo_base"], r["codigo"])),
        "divergencias": sorted(divergencias, key=lambda r: (r["ref"], r["codigo"])),
    }
    return payload


# ============================================================
# ESTRUTURA
# ============================================================

def _index_children_desc(comp: Dict[str, Any]) -> Dict[str, str]:
    """
    Indexa os filhos de uma composição em um mapa:
        { codigo_base -> descricao_original_strip }

    - Normaliza o código de cada filho com `_canon`.
    - Não recursivo: compara apenas o 1º nível de filhos (comportamento do validador antigo).
    - A descrição é mantida "crua" (apenas `strip`), pois a normalização ocorre na comparação.
    """
    out: Dict[str, str] = {}
    for ch in comp.get("filhos", []) or []:
        raw = ch.get("codigo")
        code = _canon(raw)
        out[code] = str(ch.get("descricao") or "").strip()
    return out


def _norm_parent_map(base: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Normaliza as chaves (códigos de pais) de uma base de referência:
        { codigo_base -> comp_dict }

    Isso evita falhas de match por diferenças de formatação dos códigos.
    """
    return { _canon(k): v for k, v in (base or {}).items() }


def consolidar_estrutura(
    orc_estr: Dict[str, Dict[str, Any]],
    sin_estr: Dict[str, Dict[str, Any]],
    sud_estr: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compara estrutura (pais/filhos) do ORÇAMENTO contra a base ligada ao 'banco' do pai.

    Política de comparação:
      - Se o pai no Orçamento indicar banco ≈ "SINAPI", compara apenas com SINAPI.
      - Se indicar banco ≈ "SUDECAP", compara apenas com SUDECAP.
      - Se o banco estiver vazio/inespecífico:
          • se o pai existir apenas em uma base, usa-a (auto-detecção),
          • se existir em ambas ou em nenhuma, ignora (para não gerar falsos negativos).

    Saída:
      - meta/resumo (contagem de comparados/ignorados),
      - "divergencias": para cada pai divergente, inclui:
          • ref ("SINAPI"/"SUDECAP"),
          • pai_codigo, pai_desc_a, pai_desc_b,
          • filhos_missing, filhos_extra,
          • filhos_desc_mismatch: lista de {codigo, a_desc, b_desc}.
    """
    divergencias: List[Dict[str, Any]] = []
    sinapi_comp = sudecap_comp = 0
    ignorados_por_banco = 0

    sin_norm = _norm_parent_map(sin_estr)
    sud_norm = _norm_parent_map(sud_estr)

    for key, comp_a in (orc_estr or {}).items():
        pai_orc = comp_a.get("pai_codigo") or key
        pai_base = _canon(pai_orc)
        banco_a = _bank_norm(comp_a.get("banco"))

        # Auto-detecção quando o banco do pai não está presente/normalizável
        if banco_a is None:
            in_sin = pai_base in sin_norm
            in_sud = pai_base in sud_norm
            if in_sin and not in_sud:
                banco_a = "SINAPI"
            elif in_sud and not in_sin:
                banco_a = "SUDECAP"
            else:
                ignorados_por_banco += 1
                continue  # indecidível sem risco de falso negativo

        # Seleciona a base de referência alvo conforme o banco
        if banco_a == "SINAPI":
            base_ref = sin_norm
            ref_tag = "SINAPI"
            sinapi_comp += 1
        elif banco_a == "SUDECAP":
            base_ref = sud_norm
            ref_tag = "SUDECAP"
            sudecap_comp += 1
        else:
            ignorados_por_banco += 1
            continue

        comp_b = base_ref.get(pai_base)
        idx_a = _index_children_desc(comp_a)

        if comp_b is None:
            # Pai inexistente na base de referência: todos os filhos de A são "missing"
            if idx_a:
                divergencias.append({
                    "ref": ref_tag,
                    "pai_codigo": pai_base,
                    "pai_desc_a": comp_a.get("descricao"),
                    "pai_desc_b": None,
                    "filhos_missing": sorted(idx_a.keys()),
                    "filhos_extra": [],
                    "filhos_desc_mismatch": [],
                })
            continue

        # Pai encontrado na base: comparar apenas o 1º nível de filhos
        idx_b = _index_children_desc(comp_b)
        set_a, set_b = set(idx_a.keys()), set(idx_b.keys())

        filhos_missing = sorted(set_a - set_b)   # filhos que existem no Orçamento e faltam na base
        filhos_extra   = sorted(set_b - set_a)   # filhos que existem na base e faltam no Orçamento

        filhos_desc_mismatch: List[Dict[str, str]] = []
        for code in sorted(set_a & set_b):
            da = idx_a[code]
            db = idx_b[code]
            if norm_text(da) != norm_text(db):
                filhos_desc_mismatch.append({"codigo": code, "a_desc": da, "b_desc": db})

        if filhos_missing or filhos_extra or filhos_desc_mismatch:
            divergencias.append({
                "ref": ref_tag,
                "pai_codigo": pai_base,
                "pai_desc_a": comp_a.get("descricao"),
                "pai_desc_b": comp_b.get("descricao"),
                "filhos_missing": filhos_missing,
                "filhos_extra": filhos_extra,
                "filhos_desc_mismatch": filhos_desc_mismatch,
            })

    payload = {
        "meta": {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds")},
        "resumo": {
            "comparados": {"sinapi": sinapi_comp, "sudecap": sudecap_comp},
            "ignorados_por_banco": ignorados_por_banco,
        },
        "divergencias": sorted(divergencias, key=lambda r: (r["ref"], r["pai_codigo"])),
    }
    return payload
