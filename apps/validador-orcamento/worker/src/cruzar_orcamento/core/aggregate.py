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

    - "SINAPI"  se contiver "sinapi"
    - "SUDECAP" se contiver "sudecap"
    - "SECID"   se contiver "secid"
    - None      caso ausente/não suportado (SBC, CPOS/CDHU, etc.)
    """
    if not banco:
        return None
    s = str(banco).strip().casefold()
    if "sinapi" in s:
        return "SINAPI"
    if "sudecap" in s:
        return "SUDECAP"
    if "secid" in s:
        return "SECID"
    return None


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

    # 3) descrição
    if comparar_descricao:
        if norm_text(a_desc) != norm_text(b_desc or ""):
            motivos.append("DESCRICAO_DIVERGENTE")
            extras["a_desc"] = a_desc
            if b_desc is not None:
                extras["b_desc"] = b_desc

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
    Monta o bloco de comparação para uma referência (qualquer banco).
    """
    b_desc = ref_item.get("descricao") if ref_item else None
    b_val = ref_item.get("valor_unit") if ref_item else None
    ok, extras = _compare_precos(a_desc, a_val, b_desc, b_val, tol_rel, comparar_descricao)
    out: Dict[str, Any] = {"valor": b_val, "ok": ok}
    if not ok:
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
    Versão legada: ORÇAMENTO vs (SINAPI/SUDECAP).
    Mantida por retrocompatibilidade.
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
            ignorados_por_banco += 1
            sin_block = {"nao_aplicavel": True}
            sud_block = {"nao_aplicavel": True}

        itens.append({
            "codigo": str(codigo_orc),
            "codigo_base": codigo_base,
            "a_banco": a.get("banco"),
            "a_desc": a_desc,
            "a_valor": a_val,
            "sinapi": sin_block,
            "sudecap": sud_block,
        })

    divergencias: List[Dict[str, Any]] = []
    for it in itens:
        sb = it["sinapi"]
        if not sb.get("nao_aplicavel") and not sb.get("ok"):
            d = {"ref": "SINAPI", "codigo": it["codigo_base"]}
            for k in ("motivos", "dif_abs", "dif_rel", "dir", "a_desc", "b_desc"):
                v = sb.get(k)
                if v is not None:
                    d[k] = v
            divergencias.append(d)

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


def consolidar_precos_multi(
    orc: Dict[str, Dict[str, Any]],
    bancos: Dict[str, Dict[str, Dict[str, Any]]],
    *,
    tol_rel: float = 0.05,
    comparar_descricao: bool = True,
) -> Dict[str, Any]:
    """
    Versão generalizada: aceita várias bases em `bancos`, p.ex.:
        {"SINAPI": sin, "SUDECAP": sud, "SECID": secid}

    Regras de comparação:
      - Só compara com o banco indicado em a['banco'] (normalizado por _bank_norm).
      - Os demais bancos entram como {"nao_aplicavel": true}.
      - Se o orçamento não indicar banco suportado, ignora (para evitar falsos negativos).
    """
    # normaliza chaves dos bancos (maiúsculas)
    banks_upper = {k.upper(): v for k, v in (bancos or {}).items()}
    bank_keys_sorted = sorted(banks_upper.keys())  # ordem estável

    # contadores por banco
    comparados = {k: 0 for k in bank_keys_sorted}
    oks = {f"{k.lower()}_ok": 0 for k in bank_keys_sorted}

    itens: List[Dict[str, Any]] = []
    ignorados_por_banco = 0

    for key, a in orc.items():
        codigo_orc = a.get("codigo") or key
        codigo_base = _canon(codigo_orc)
        a_desc = a.get("descricao", "")
        a_val = _to_float(a.get("valor_unit"))
        a_banco = _bank_norm(a.get("banco"))  # "SINAPI"/"SUDECAP"/"SECID"/None

        # busca em todas as bases (pelo canônico; fallback no bruto)
        refs: Dict[str, Optional[Dict[str, Any]]] = {}
        for tag, base in banks_upper.items():
            refs[tag] = base.get(codigo_base) or base.get(codigo_orc) or base.get(key)

        blocks: Dict[str, Any] = {}
        if a_banco and a_banco in banks_upper:
            # compara apenas com o banco indicado; os demais ficam nao_aplicavel
            comparados[a_banco] += 1
            for tag in bank_keys_sorted:
                if tag == a_banco:
                    blk = _build_ref_block(a_desc, a_val, refs[tag], tol_rel, comparar_descricao)
                    if blk.get("ok"):
                        oks[f"{tag.lower()}_ok"] += 1
                    blocks[tag.lower()] = blk
                else:
                    blocks[tag.lower()] = {"nao_aplicavel": True}
        else:
            ignorados_por_banco += 1
            for tag in bank_keys_sorted:
                blocks[tag.lower()] = {"nao_aplicavel": True}

        item = {
            "codigo": str(codigo_orc),
            "codigo_base": codigo_base,
            "a_banco": a.get("banco"),
            "a_desc": a_desc,
            "a_valor": a_val,
        }
        item.update(blocks)
        itens.append(item)

    # Divergências
    divergencias: List[Dict[str, Any]] = []
    for it in itens:
        for tag in bank_keys_sorted:
            blk = it[tag.lower()]
            if not blk.get("nao_aplicavel") and not blk.get("ok"):
                d = {"ref": tag, "codigo": it["codigo_base"]}
                for k in ("motivos", "dif_abs", "dif_rel", "dir", "a_desc", "b_desc"):
                    v = blk.get(k)
                    if v is not None:
                        d[k] = v
                divergencias.append(d)

    resumo_comp = {k.lower(): comparados[k] for k in bank_keys_sorted}
    resumo_ok = {k.lower() + "_ok": oks[k.lower() + "_ok"] for k in bank_keys_sorted}

    payload: Dict[str, Any] = {
        "meta": {
            "tol_rel": tol_rel,
            "comparar_descricao": comparar_descricao,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
        "resumo": {
            "itens_orc": len(itens),
            "comparados": resumo_comp,
            "ok": resumo_ok,
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
    Indexa os filhos de uma composição em um mapa: { codigo_base -> descricao }
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
    """
    return { _canon(k): v for k, v in (base or {}).items() }


def consolidar_estrutura(
    orc_estr: Dict[str, Dict[str, Any]],
    sin_estr: Dict[str, Dict[str, Any]],
    sud_estr: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Versão legada (SINAPI/SUDECAP). Mantida por retrocompatibilidade.
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

        # Auto-detecção simples entre SINAPI/SUDECAP
        if banco_a is None:
            in_sin = pai_base in sin_norm
            in_sud = pai_base in sud_norm
            if in_sin and not in_sud:
                banco_a = "SINAPI"
            elif in_sud and not in_sin:
                banco_a = "SUDECAP"
            else:
                ignorados_por_banco += 1
                continue

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

        idx_b = _index_children_desc(comp_b)
        set_a, set_b = set(idx_a.keys()), set(idx_b.keys())

        filhos_missing = sorted(set_a - set_b)
        filhos_extra   = sorted(set_b - set_a)

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


def consolidar_estrutura_multi(
    orc_estr: Dict[str, Dict[str, Any]],
    bancos: Dict[str, Dict[str, Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Versão generalizada para estrutura: aceita múltiplas bases em `bancos`.
    - Se o pai do orçamento indicar banco suportado, compara com aquele.
    - Se não indicar, tenta auto-detectar: se o pai existe em **exatamente uma**
      das bases, usa-a; caso contrário, ignora (para evitar falsos negativos).
    """
    banks_upper = {k.upper(): _norm_parent_map(v) for k, v in (bancos or {}).items()}
    bank_keys_sorted = sorted(banks_upper.keys())

    comparados = {k: 0 for k in bank_keys_sorted}
    ignorados_por_banco = 0
    divergencias: List[Dict[str, Any]] = []

    for key, comp_a in (orc_estr or {}).items():
        pai_orc = comp_a.get("pai_codigo") or key
        pai_base = _canon(pai_orc)
        banco_a = _bank_norm(comp_a.get("banco"))  # pode ser None

        target_tag: Optional[str] = None

        if banco_a and banco_a in banks_upper:
            target_tag = banco_a
        else:
            # auto-detecção: exatamente uma base contém o pai
            hits = [tag for tag in bank_keys_sorted if pai_base in banks_upper[tag]]
            if len(hits) == 1:
                target_tag = hits[0]

        if not target_tag:
            ignorados_por_banco += 1
            continue

        base_ref = banks_upper[target_tag]
        comparados[target_tag] += 1

        comp_b = base_ref.get(pai_base)
        idx_a = _index_children_desc(comp_a)

        if comp_b is None:
            if idx_a:
                divergencias.append({
                    "ref": target_tag,
                    "pai_codigo": pai_base,
                    "pai_desc_a": comp_a.get("descricao"),
                    "pai_desc_b": None,
                    "filhos_missing": sorted(idx_a.keys()),
                    "filhos_extra": [],
                    "filhos_desc_mismatch": [],
                })
            continue

        idx_b = _index_children_desc(comp_b)
        set_a, set_b = set(idx_a.keys()), set(idx_b.keys())

        filhos_missing = sorted(set_a - set_b)
        filhos_extra   = sorted(set_b - set_a)

        filhos_desc_mismatch: List[Dict[str, str]] = []
        for code in sorted(set_a & set_b):
            da = idx_a[code]
            db = idx_b[code]
            if norm_text(da) != norm_text(db):
                filhos_desc_mismatch.append({"codigo": code, "a_desc": da, "b_desc": db})

        if filhos_missing or filhos_extra or filhos_desc_mismatch:
            divergencias.append({
                "ref": target_tag,
                "pai_codigo": pai_base,
                "pai_desc_a": comp_a.get("descricao"),
                "pai_desc_b": comp_b.get("descricao"),
                "filhos_missing": filhos_missing,
                "filhos_extra": filhos_extra,
                "filhos_desc_mismatch": filhos_desc_mismatch,
            })

    resumo_comp = {k.lower(): comparados[k] for k in bank_keys_sorted}
    payload = {
        "meta": {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds")},
        "resumo": {
            "comparados": resumo_comp,
            "ignorados_por_banco": ignorados_por_banco,
        },
        "divergencias": sorted(divergencias, key=lambda r: (r["ref"], r["pai_codigo"])),
    }
    return payload
