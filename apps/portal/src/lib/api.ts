// apps/portal/src/lib/api.ts
const fallback = `${location.protocol}//${location.hostname}:8001`;

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL?.trim() || fallback
).replace(/\/$/, ""); // sem barra final

export type FileEntry = { name: string; path: string; size: number; mtime: number };
export type FilesResponse = { output_dir: string; files: FileEntry[] };

export async function health() {
  const r = await fetch(`${API_BASE_URL}/health`);
  if (!r.ok) throw new Error(`/health ${r.status}`);
  return r.json();
}

export async function listFiles(): Promise<FilesResponse> {
  const r = await fetch(`${API_BASE_URL}/files`);
  if (!r.ok) throw new Error(`/files ${r.status}`);
  return r.json();
}

export async function getPrecos() {
  const r = await fetch(`${API_BASE_URL}/precos`);
  if (!r.ok) throw new Error(`/precos ${r.status}`);
  return r.json();
}

export async function getEstrutura() {
  const r = await fetch(`${API_BASE_URL}/estrutura`);
  if (!r.ok) throw new Error(`/estrutura ${r.status}`);
  return r.json();
}
