const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001";

export type JobCreate =
  | {
      op: "precos_manual";
      orc: string;
      ref: string;
      ref_type: "SINAPI" | "SUDECAP";
      banco: "SINAPI" | "SUDECAP";
      tol_rel: number;
      out: string;
    }
  | {
      op: "precos_auto";
      orc: string;
      tol_rel: number;
      out_dir: string;
    }
  | {
      op: "estrutura";
      orc: string;
      banco_a: "SINAPI" | "SUDECAP";
      base: string;
      base_type: "SINAPI" | "SUDECAP";
      out: string;
    };

export type JobOut = { id: string; status: string; artifact?: unknown };

export async function createJob(payload: JobCreate): Promise<JobOut> {
  const r = await fetch(`${BASE}/jobs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`Falha ao criar job: ${r.status}`);
  return r.json();
}

export async function getJob(id: string): Promise<JobOut> {
  const r = await fetch(`${BASE}/jobs/${id}`);
  if (!r.ok) throw new Error(`Job ${id} não encontrado`);
  return r.json();
}
