export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  `${window.location.protocol}//${window.location.hostname}:8001`;

export type Job = { id: string; status: string };

export async function getJob(id: string): Promise<Job> {
  const res = await fetch(`${API_BASE_URL}/jobs/${id}`);
  if (!res.ok) throw new Error(`GET /jobs/${id} falhou: ${res.status}`);
  return res.json();
}

export async function getJobResult(id: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/jobs/${id}/result`);
  if (!res.ok) throw new Error(`GET /jobs/${id}/result falhou: ${res.status}`);
  return res.json();
}
