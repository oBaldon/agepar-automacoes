# agepar-automacoes

Automação de validação de orçamento com arquitetura em **monorepo**, serviços em **Docker**, backend **FastAPI** + **Redis/RQ**, **worker** em Python, e **portal** em Vite/React/TS para operacionalizar os fluxos.

## Sumário

* [Visão geral](#visão-geral)
* [Estrutura do monorepo](#estrutura-do-monorepo)
* [Arquitetura & Fluxo](#arquitetura--fluxo)
* [Pré-requisitos](#pré-requisitos)
* [Executando com Docker](#executando-com-docker)
* [Frontend (portal)](#frontend-portal)
* [API (FastAPI)](#api-fastapi)
* [Worker (RQ)](#worker-rq)
* [Volumes & Permissões](#volumes--permissões)
* [Rede & CORS](#rede--cors)
* [Diagnóstico & Troubleshooting](#diagnóstico--troubleshooting)
* [Comandos úteis](#comandos-úteis)
* [Roadmap](#roadmap)

---

## Visão geral

O monorepo abriga:

* **Portal**: interface única (Vite + React + TS) para envio e acompanhamento de jobs.
* **API**: expõe endpoints para **criação/consulta de jobs** e leitura dos **artefatos** produzidos.
* **Worker**: consome jobs de uma fila **RQ** no **Redis**, processa planilhas (Orçamento, SINAPI, SUDECAP) e gera JSONs em `/app/output`.

O layout-base do monorepo (apps, packages, infra) já estava esboçado e foi mantido/expandido.&#x20;

---

## Estrutura do monorepo

```
apps/
  portal/                       # Vite + React + TS
  validador-orcamento/
    api/                        # FastAPI (RQ client)
      src/main.py
      Dockerfile
      requirements.txt
    worker/                     # Worker RQ (Python)
      src/tasks.py
      src/runner.py
      Dockerfile
      requirements.txt
packages/
  tokens/                       # Design tokens (CSS)
  ui/                           # Componentes UI compartilhados
infra/
  nginx/                        # Gateway reverso (futuro)
```

> Observação: havia referência a `infra/nginx` e `docker-compose.yml` no README original; mantivemos o padrão e preparamos os serviços para futura orquestração centralizada.&#x20;

---

## Arquitetura & Fluxo

1. **Portal** envia o **payload JSON** para `POST /jobs` (API).
2. **API** enfileira a chamada (ex.: `src.tasks.run_precos_auto`) no **RQ/Redis**, retornando `job.id`.&#x20;
3. **Worker**:

   * Lê os arquivos nas pastas montadas (ex.: `/app/data`).
   * Processa e grava o resultado em **`/app/output/*.json`** (ex.: `precos.json`, `estrutura.json`).&#x20;
   * Salva o caminho do artefato nos metadados do job (para a API localizar).&#x20;
4. **Portal** faz polling de `GET /jobs/{id}` até `status=finished` e, então, busca `GET /jobs/{id}/result` para renderizar/baixar o JSON final.

---

## Pré-requisitos

* **Docker** e **Docker Network** para comunicação entre containers:

  ```bash
  docker network create agepar-net || true
  ```
* O portal em desenvolvimento pode rodar fora do Docker (Vite dev server).

---

## Executando com Docker

### 1) Redis

```bash
docker run -d --name redis --network agepar-net -p 6379:6379 redis:7-alpine
```

### 2) Build das imagens

```bash
# Worker
docker build -t agepar/validador-worker:dev apps/validador-orcamento/worker

# API
docker build -t agepar/validador-api:dev apps/validador-orcamento/api
```

### 3) Volumes locais

```bash
ROOT="$PWD"
DATA="$ROOT/apps/validador-orcamento/worker/data"
OUT="$ROOT/apps/validador-orcamento/worker/output"
mkdir -p "$DATA" "$OUT"
```

### 4) Subir **Worker** (monta data rw/ro e output rw)

```bash
docker run -d --name validador-worker \
  --network agepar-net \
  -e REDIS_URL=redis://redis:6379/1 \
  -e QUEUE_NAME=validador \
  -v "$DATA:/app/data:ro" \
  -v "$OUT:/app/output" \
  agepar/validador-worker:dev
```

### 5) Subir **API** (lê o mesmo output como read-only)

```bash
docker run -d --name validador-api \
  --network agepar-net -p 8001:8000 \
  -e REDIS_URL=redis://redis:6379/1 \
  -e CORS_ORIGINS="http://localhost:5173,http://192.168.18.187:5173,http://10.59.1.81:5173" \
  -v "$OUT:/app/output:ro" \
  agepar/validador-api:dev
```

> **Dica**: Em caso de conflito de nomes, remova containers antigos com `docker rm -f <nome>`.

---

## Frontend (portal)

* Projeto Vite + React + TS.
* Resolve a base da API como:

  * `VITE_API_BASE_URL` (se definido), **senão** usa `location.hostname:8001` (ajudando a funcionar em redes 10.59.\* ou 192.168.\* sem reconfigurar).
* **Dev server** exposto na rede:

  ```bash
  cd apps/portal
  pnpm i
  pnpm dev -- --host 0.0.0.0 --port 5173 --strictPort
  ```

Páginas principais:

* **Validador de Orçamento**: formulário para escolher operação (preços/estrutura), caminhos e parâmetros.
* **JobResult**: polling + renderização do JSON (copiar/baixar).
* **Arquivos** (opcional): lista o conteúdo de `/files` (output da API).

Histórico local:

* `src/lib/recentJobs.ts` guarda os últimos IDs em `localStorage` e emite o evento `recent-jobs-updated`.

---

## API (FastAPI)

### Rotas principais

* `GET /health` — status do serviço e do Redis.&#x20;
* `GET /files` — lista JSONs em `/app/output` (mais novos primeiro, com `size_human` e `mtime_iso`).&#x20;
* `POST /jobs` — cria e enfileira um job (RQ).&#x20;
* `GET /jobs/{id}` — retorna `{id, status}` (queued/started/finished/failed…).&#x20;
* `GET /jobs/{id}/result` — devolve o JSON correspondente ao artefato final salvo pelo worker.&#x20;

### Exemplo – criar job (preços automático)

```bash
curl -s -X POST http://localhost:8001/jobs \
  -H 'content-type: application/json' \
  -d '{
    "op": "precos_auto",
    "orc": "data/orcamento.xlsx",
    "sudecap": "data/sudecap_preco.xls",
    "sinapi": "data/sinapi_ccd.xlsx",
    "tol_rel": 0.05,
    "comparar_desc": true,
    "out_dir": "output"
  }'
```

> A API valida campos obrigatórios por operação e enfileira com `job_timeout`, `result_ttl` e `failure_ttl` razoáveis, retornando `201` com **Location** para `/jobs/{id}`.&#x20;

### Exemplo – criar job (estrutura automático)

```bash
curl -s -X POST http://localhost:8001/jobs \
  -H 'content-type: application/json' \
  -d '{
    "op": "estrutura_auto",
    "orc": "data/orcamento.xlsx",
    "sudecap": "data/sudecap_comp.xls",
    "sinapi": "data/sinapi_estrutura.xlsx",
    "out_dir": "output"
  }'
```

> Mesma semântica do caso de preços, focando nos arquivos de **estrutura**.&#x20;

### Consultar status e resultado

```bash
# status
curl -s http://localhost:8001/jobs/<JOB_ID>

# resultado (após finished)
curl -s http://localhost:8001/jobs/<JOB_ID>/result
```

---

## Worker (RQ)

O worker sobe com `src/runner.py`, aguarda o Redis ficar disponível e inicia o processamento da fila configurada (padrão `validador`).&#x20;

### Tarefas suportadas

* `run_precos_auto(orc, sudecap, sinapi, tol_rel=0.05, out_dir="output", comparar_desc=True)`
  Consolida preços, gera **`precos.json`** e adiciona metadados (`generated_at`, `inputs`, `params`).&#x20;
* `run_estrutura_auto(orc, sudecap, sinapi, out_dir="output")`
  Compara a estrutura (pai + filhos 1º nível), gera **`estrutura.json`** com metadados.&#x20;

Ambas:

* Normalizam caminhos relativos/absolutos sob `/app`.
* Garantem criação de `out_dir` e validam existência dos arquivos.&#x20;

---

## Volumes & Permissões

* **Worker** escreve em `/app/output` (volume **rw**).
* **API** lê **o mesmo** volume em `/app/output` (**ro**).
* Garanta que **ambos containers** montam **a mesma pasta do host** no **mesmo destino** do container; é essencial para o `/jobs/{id}/result` não dar 404.
  (Dica: cheque com `docker inspect -f '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}' <nome>`.)

---

## Rede & CORS

* Containers na mesma rede Docker: `--network agepar-net`.
* **CORS** configurado via `CORS_ORIGINS` (se não definir, permite `*` em dev).&#x20;
* O **portal** resolve `API_BASE_URL` para `VITE_API_BASE_URL` **ou** fallback `http(s)://<hostname>:8001`, permitindo usar IP de cabo (10.59.*) ou Wi-Fi (192.168.*) sem ajustes adicionais.

---

## Diagnóstico & Troubleshooting

* **Saúde da API**:

  ```bash
  curl -s http://<host>:8001/health
  ```
* **Ver artefatos**:

  ```bash
  docker exec -it validador-worker ls -lh /app/output
  docker exec -it validador-api    ls -lh /app/output
  ```

  Ambos devem listar os mesmos `precos.json` e/ou `estrutura.json`.
* **Logs**:

  ```bash
  docker logs -f validador-worker
  docker logs -f validador-api
  ```
* **Conflito de nomes**: remova containers antigos com `docker rm -f <nome>`.
* **Permissões**: mantenha o volume `output` gravável pelo worker; a API monta `:ro`.

---

## Comandos úteis

```bash
# Status rápido
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'

# Rebuild imagens
docker build -t agepar/validador-worker:dev apps/validador-orcamento/worker
docker build -t agepar/validador-api:dev    apps/validador-orcamento/api

# Teste de criação de job
curl -s -X POST http://localhost:8001/jobs -H 'content-type: application/json' -d '{...}'
curl -s http://localhost:8001/jobs/<ID>
curl -s http://localhost:8001/jobs/<ID>/result
```

---

## Roadmap

* **Uploads de arquivos pela API** (`multipart/form-data`) para não depender de caminhos montados — hoje os caminhos são resolvidos no **worker** (ex.: `data/orcamento.xlsx`).
* **Gateway NGINX** (compose) para expor portal + API sob um único host.
* **Armazenamento de artefatos** (MinIO/S3) e expiração/GC configurável.
* **CI/CD** (build/push de imagens).

---

### Referências do repositório

* Estrutura do monorepo no README original.&#x20;
* Exemplos e validação de payload em `src/main.py` (API).&#x20;
* Rotas de status/files/health.&#x20;
* Metadados de artefato do job no worker.&#x20;
* Normalização de caminhos e geração de artefatos em `tasks.py`.&#x20;

---

> Este README reflete o **estado estável atual**: criação de jobs via `POST /jobs` usando **caminhos** (não upload direto), processamento no **worker** e leitura de artefatos via `/jobs/{id}/result`.
