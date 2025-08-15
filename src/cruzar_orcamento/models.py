# src/cruzar_orcamento/models.py
from __future__ import annotations

from typing import TypedDict, NotRequired, Dict, List


# =========================
# Itens (cruzamento de preços)
# =========================
class Item(TypedDict):
    """
    Esquema canônico de um item (usado no cruzamento de valores).
    """
    codigo: str
    descricao: str
    valor_unit: float
    # Banco de referência ao qual o item do orçamento pertence (ex.: "SUDECAP", "SINAPI").
    # Mantido como opcional porque nem todo orçamento traz essa coluna.
    banco: NotRequired[str]
    # Origem do registro, p.ex. "ORCAMENTO", "SUDECAP", "SINAPI"
    fonte: str


# =========================
# Estrutura de composições (1º nível)
# =========================
class ChildSpec(TypedDict):
    """
    Filho imediato de uma composição (pode ser Insumo ou Composição Auxiliar).
    Para validação de ESTRUTURA só comparamos código e descrição.
    """
    codigo: str
    descricao: str


class CompEstrutura(TypedDict):
    """
    Estrutura de uma composição 'mestra': pai + lista de filhos de 1º nível.
    """
    # Chave do match
    codigo: str
    # Descrição da composição mestra (apenas para exibir/depurar)
    descricao: str
    # Filhos imediatos (ordem não importa)
    filhos: List[ChildSpec]
    # Origem (ex.: "ORCAMENTO", "SUDECAP", "SINAPI")
    fonte: str


# Dicionários de acesso rápido
EstruturaDict = Dict[str, CompEstrutura]   # código do pai -> estrutura
CanonDict     = Dict[str, Item]            # código -> item (para cruzamento de valores)


__all__ = [
    "Item",
    "ChildSpec",
    "CompEstrutura",
    "EstruturaDict",
    "CanonDict",
]
