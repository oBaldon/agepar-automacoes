// apps/portal/src/lib/api.ts

// Fallback: mesmo host do front, porta 8001
const fallback = `${location.protocol}//${location.hostname}:8001`;

// Base da API (sem barra final)
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL?.trim() || fallback
).replace(/\/$/, "");

// --------------------
// Tipos
// --------------------
export type JobStatus =
  | "queued"
  | "started"
  | "deferred"
  | "finished"
  | "failed"
  | string;

export type Job = { id: string; status: JobStatus };

export type FileEntry = {
  name: string;
  path: string;
  size: number;
  mtime: number;
  // campos extras que a API agora devolve
  size_human?: string;
  mtime_iso?: string;
};

export type FilesResponse = {
  output_dir: string;
  files: FileEntry[];
  count?: number; // a API pode enviar "count"
};

// payloads suportados pelos jobs
export type PrecosAutoPayload = {
  op: "precos_auto";
  orc: string;       // ex.: "data/orcamento.xlsx"
  sudecap: string;   // ex.: "data/sudecap_preco.xls"
  sinapi: string;    // ex.: "data/sinapi_ccd.xlsx"
  tol_rel?: number;  // ex.: 0.05
  comparar_desc?: boolean; // default = true
  out_dir?: string;  // ex.: "output"
};

export type EstruturaAutoPayload = {
  op: "estrutura_auto";
  orc: string;
  sudecap: string;
  sinapi: string;
  out_dir?: string;  // ex.: "output"
};

export type CreateJobPayload = PrecosAutoPayload | EstruturaAutoPayload;

// --------------------
// Helper de fetch
// --------------------
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE_URL}${path}`, {
    // Accept ajuda proxies a retornarem JSON corretamente
    headers: { Accept: "application/json", ...(init?.headers || {}) },
    ...init,
  });

  if (!r.ok) {
    let msg = `${path} ${r.status}`;
    try {
      const txt = await r.text();
      if (txt) {
        try {
          const parsed = JSON.parse(txt);
          msg = (parsed && (parsed.detail || parsed.message)) || txt;
        } catch {
          msg = txt;
        }
      }
    } catch { /* noop */ }
    throw new Error(msg);
  }

  // Em caso de 204 No Content
  if (r.status === 204) return undefined as unknown as T;

  // Se, por algum motivo, não vier JSON, devolve texto bruto
  const ct = r.headers.get("content-type") || "";
  if (!ct.toLowerCase().includes("application/json")) {
    const txt = await r.text();
    return txt as unknown as T;
  }

  return r.json() as Promise<T>;
}

// --------------------
// Endpoints
// --------------------
export async function health() {
  return request<Record<string, unknown>>(`/health`);
}

export async function listFiles(): Promise<FilesResponse> {
  return request<FilesResponse>(`/files`);
}

// ========== JOBS ==========
export async function createJob(payload: CreateJobPayload): Promise<Job> {
  return request<Job>(`/jobs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getJob(id: string): Promise<Job> {
  return request<Job>(`/jobs/${encodeURIComponent(id)}`);
}

export async function getJobResult<T = unknown>(id: string): Promise<T> {
  return request<T>(`/jobs/${encodeURIComponent(id)}/result`);
}

// ========== LEGADO (se ainda existir uso no front) ==========
export async function getPrecos() {
  return request(`/precos`);
}

export async function getEstrutura() {
  return request(`/estrutura`);
}
