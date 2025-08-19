// apps/portal/src/lib/api.ts
const fallback = `${location.protocol}//${location.hostname}:8001`;

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL?.trim() || fallback
).replace(/\/$/, ""); // sem barra no final

export type Job = { id: string; status: string };

export async function health() {
  const r = await fetch(`${API_BASE_URL}/health`);
  if (!r.ok) throw new Error(`/health ${r.status}`);
  return r.json();
}

export async function createJob(payload: any) {
  const r = await fetch(`${API_BASE_URL}/jobs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as Job;
}

export async function getJob(id: string) {
  const r = await fetch(`${API_BASE_URL}/jobs/${id}`);
  if (!r.ok) throw new Error(`/jobs/${id} ${r.status}`);
  return (await r.json()) as Job;
}

export async function getJobResult(id: string) {
  const r = await fetch(`${API_BASE_URL}/jobs/${id}/result`);
  if (!r.ok) throw new Error(`/jobs/${id}/result ${r.status}`);
  return r.json();
}
