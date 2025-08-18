import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

type Job = { id: string; status: string };

export default function JobResult(){
  const { id } = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if(!id) return;
    fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'}/jobs/${id}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.statusText))
      .then(setJob)
      .catch((e) => setError(String(e)));
  }, [id]);

  return (
    <main className="p-6 max-w-5xl mx-auto">
      <h1 className="text-xl font-semibold mb-4">Resultado do Job</h1>
      <div className="card">
        {!id && <p>Nenhum ID informado.</p>}
        {error && <p className="text-red-600">Erro: {error}</p>}
        {job && (
          <div className="space-y-2">
            <div><b>ID:</b> {job.id}</div>
            <div><b>Status:</b> {job.status}</div>
            <p className="text-sm text-[var(--muted)]">
              (Em breve: renderizar o JSON de saída quando o status for <i>finished</i>.)
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
