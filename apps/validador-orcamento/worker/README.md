# cruzar-orcamento

Ferramentas para **cruzar preços** e **validar a estrutura de composições** entre um **Orçamento** (planilha do cliente) e bancos de referência **SUDECAP** e **SINAPI**.

> Saídas em **JSON**, adequadas para consumo por aplicações web ou pipelines de dados.

---

## Sumário
- [Visão geral](#visão-geral)
- [Instalação](#instalação)
- [Formato dos arquivos de entrada](#formato-dos-arquivos-de-entrada)
  - [Orçamento (Composições)](#orçamento-composições)
  - [SINAPI (Analítico)](#sinapi-analítico)
  - [SUDECAP (Relatório de Composições)](#sudecap-relatório-de-composições)
- [Como usar (CLI)](#como-usar-cli)
  - [Preços — cruzamento manual](#preços--cruzamento-manual)
  - [Preços — cruzamento automático](#preços--cruzamento-automático)
  - [Estrutura — validação (pais/filhos de 1º nível)](#estrutura--validação-paisfilhos-de-1º-nível)
- [Esquemas de JSON](#esquemas-de-json)
  - [Saída — Preços](#saída--preços)
  - [Saída — Estrutura](#saída--estrutura)
- [Dicas e resolução de problemas](#dicas-e-resolução-de-problemas)
- [Licença](#licença)

---

## Visão geral

O projeto possui **adapters** para ler e normalizar planilhas de diferentes origens (Orçamento, SINAPI, SUDECAP), **validators/processors** para aplicar as regras de comparação e **exporters** para gravar os resultados em **JSON**.

Funcionalidades principais:

1. **Cruzamento de preços** por **código** (com filtro opcional por `banco` no Orçamento) entre:
   - Orçamento × SINAPI
   - Orçamento × SUDECAP

2. **Validação de estrutura** de composições no **1º nível** (pais → filhos), comparando:
   - Orçamento (apenas composições de um banco específico) × SINAPI (aba *Analítico*)
   - Orçamento (apenas composições de um banco específico) × SUDECAP (Relatório de Composições)

Saídas sempre em **JSON** dentro de `output/` (configurável por parâmetro).

---

## Instalação

Requer **Python 3.10+** (recomendado 3.12).

```bash
git clone https://github.com/oBaldon/cruzar-orcamento.git
cd cruzar-orcamento
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> Para leitura de arquivos **.xls** (SUDECAP), é necessário o pacote `xlrd`.
> Se houver erro ao instalar, você pode converter o `.xls` para `.xlsx` manualmente e usar o arquivo convertido.

---

## Formato dos arquivos de entrada

### Orçamento (Composições)

- Ler da(s) aba(s) que contenham a palavra **“Composições”** (varredura automática).
- Deve conter colunas reconhecíveis como **Código**, **Descrição** e **Tipo**.
- A coluna **Tipo** deve distinguir **Composição** (pai), **Composição Auxiliar** e **Insumo**.
- O **banco** da composição do Orçamento (ex.: *SINAPI*, *SUDECAP*) é utilizado para **filtrar** o que será comparado.

> Apenas o **1º nível** de filhos é considerado (não “explode” composições auxiliares).

### SINAPI (Analítico)

- Usar a aba **`Analítico`**.
- Colunas esperadas (posicionais):
  - **B**: código da composição **pai**.
  - **C**: tipo do filho (`INSUMO`/`COMPOSICAO`).
  - **D**: código do **filho**.
  - **B..G**: descrição do **pai** (concatenação).
  - **C..G**: descrição do **filho** (concatenação).

### SUDECAP (Relatório de Composições)

- Planilha com título “**Relatório de Composições de Construção**” (desonerada).
- Colunas esperadas (posicionais):
  - **A**: código da composição **pai** (quando preenchida, inicia um novo pai).
  - **B**: código do **filho** (nas linhas onde **A** está vazia).
  - **B..G**: descrição do **pai** (na linha do pai).
  - **C..G**: descrição do **filho** (nas linhas sem código em A).

> Em ambas as bases, os **códigos** são **normalizados**: remoção de sufixo `.0` e de **zeros à esquerda** quando presente.

---

## Como usar (CLI)

Todos os comandos abaixo assumem o ambiente virtual ativo e o diretório do projeto como `cwd`.

### Preços — cruzamento manual

**Orçamento × SINAPI**:

```bash
python -m src.cli precos manual   --orc "data/ORÇAMENTO.xlsx"   --ref "data/SINAPI_2025_06.xlsx"   --ref-type SINAPI   --banco SINAPI   --tol-rel 0.00   --out-json "output/cruzamento_precos_sinapi_2025_06.json"
```

**Orçamento × SUDECAP**:

```bash
python -m src.cli precos manual   --orc "data/ORÇAMENTO.xlsx"   --ref "data/SUDECAP_2025_04.xls"   --ref-type SUDECAP   --banco SUDECAP   --tol-rel 0.00   --out-json "output/cruzamento_precos_sudecap_2025_04.json"
```

### Preços — cruzamento automático

Usa os arquivos **mais recentes** do diretório `data/` no padrão `SINAPI_YYYY_MM.xlsx` e `SUDECAP_YYYY_MM.xls|xlsx`:

```bash
python -m src.cli precos auto   --orc "data/ORÇAMENTO.xlsx"   --out-dir output
```

Gera dois arquivos JSON: um para **SINAPI** e outro para **SUDECAP**.

### Estrutura — validação (pais/filhos de 1º nível)

**Orçamento (somente composições do banco SINAPI) × SINAPI (Analítico)**:

```bash
python -m src.cli estrutura validar   --orc "data/ORÇAMENTO.xlsx"   --banco-a SINAPI   --base "data/SINAPI_2025_06.xlsx"   --base-type SINAPI   --json-out "output/diverg_estrutura_sinapi.json"
```

**Orçamento (somente SUDECAP) × SUDECAP (Relatório de Composições)**:

```bash
python -m src.cli estrutura validar   --orc "data/ORÇAMENTO.xlsx"   --banco-a SUDECAP   --base "data/SUDECAP_2025_04.xls"   --base-type SUDECAP   --json-out "output/diverg_estrutura_sudecap.json"
```

> Também é possível comparar **Orçamento × Orçamento** (útil para auditoria interna) usando `--base-type ORCAMENTO`.

---

## Esquemas de JSON

### Saída — Preços

Arquivo gerado por `precos manual/auto` (exemplo de estrutura simplificada):

```json
{
  "resumo": {
    "total_linhas": 123,
    "total_divergencias": 7,
    "tol_rel": 0.0
  },
  "linhas": [
    {
      "codigo": "88316",
      "a_banco": "SINAPI",
      "a_desc": "SERVENTE COM ENCARGOS COMPLEMENTARES",
      "a_valor": 100.0,
      "b_desc": "SERVENTE COM ENCARGOS COMPLEMENTARES",
      "b_valor": 100.0,
      "match": true,
      "dif_abs": 0.0,
      "dif_rel": 0.0
    }
  ],
  "divergencias": [
    {
      "codigo": "90965",
      "motivos": ["codigo_nao_encontrado_na_referencia"]
    }
  ]
}
```

> Campos podem variar conforme a fonte; use a chave `linhas` para consumo principal e `divergencias` para destacar casos a tratar.

### Saída — Estrutura

Arquivo gerado por `estrutura validar` (por pai/compisição):

```json
[
  {
    "pai_codigo": "01.12.01",
    "pai_desc_a": "VISTORIA CAUTELAR - ÁREA CONSTRUÍDA <= 100M2",
    "pai_desc_b": "VISTORIA CAUTELAR - ÁREA CONSTRUÍDA <= 100M2",
    "filhos_missing": ["94.12.02"],
    "filhos_extra": ["94.12.03"],
    "filhos_desc_mismatch": [
      {
        "codigo": "55.20.05",
        "a_desc": "ENGENHEIRO INTERMEDIÁRIO (CARGA HORÁRIA 8H/DIA)",
        "b_desc": "ENGENHEIRO INTERMEDIÁRIO"
      }
    ]
  }
]
```

- `filhos_missing`: existem no Orçamento e **faltam** na Base.
- `filhos_extra`: existem na Base e **não** existem no Orçamento.
- `filhos_desc_mismatch`: mesmo código em ambos, mas **descrições diferentes** (normalização sem acentos e case-insensitive).

---

## Dicas e resolução de problemas

- **.xls (SUDECAP)**: instale `xlrd` ou converta o arquivo para `.xlsx`.
- **Planilhas com layouts diferentes**: os adapters aplicam heurísticas para encontrar cabeçalhos e colunas. Se algo fugir muito do padrão, ajuste o adapter correspondente:
  - `src/cruzar_orcamento/adapters/estrutura_orcamento.py`
  - `src/cruzar_orcamento/adapters/estrutura_sinapi.py`
  - `src/cruzar_orcamento/adapters/estrutura_sudecap.py`
- **Normalização de códigos**: feita em `src/cruzar_orcamento/utils/utils_code.py` (`norm_code_canonical`) — remove `.0` finais e zeros à esquerda.

---

## Licença

Projeto de uso interno.