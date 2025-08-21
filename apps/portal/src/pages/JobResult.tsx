// apps/portal/src/pages/JobResult.tsx
import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { API_BASE_URL, getJob, getJobResult, type Job } from "../lib/api";
import { pushRecent } from "../lib/recentJobs";

export default function JobResult() {
  const { id = "" } = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const pretty = useMemo(() => (data ? JSON.stringify(data, null, 2) : ""), [data]);

  async function copyJson() {
    try {
      await navigator.clipboard.writeText(pretty);
      alert("JSON copiado!");
    } catch {
      alert("Falha ao copiar.");
    }
  }

  function downloadJson() {
    const blob = new Blob([pretty], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `job_${id}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    if (!id) return;

    // registra nos recentes ao abrir
    pushRecent(id);

    let stop = false;
    let timer: number | undefined;

    async function tick() {
      try {
        setErr(null);
        const j = await getJob(id);
        setJob(j);
        document.title = `Job ${id} – ${j.status}`;

        if (j.status === "finished") {
          const r = await getJobResult(id);
          if (!stop) {
            setData(r);
            setLoading(false);
            // re-registra pra subir pro topo dos recentes
            pushRecent(id);
          }
          return;
        }

        if (j.status === "failed") {
          if (!stop) {
            setLoading(false);
            setErr("Job falhou. Verifique os logs do worker.");
          }
          return;
        }
      } catch (e: any) {
        if (!stop) setErr(e?.message ?? "Erro ao consultar job.");
      }

      if (!stop) timer = window.setTimeout(tick, 2000);
    }

    setLoading(true);
    tick();

    return () => {
      stop = true;
      if (timer) window.clearTimeout(timer);
      document.title = "Validador";
    };
  }, [id]);

  return (
    <main className="p-6 max-w-5xl mx-auto space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold">Resultado do Job</h1>
        <code className="text-xs opacity-70">{id}</code>
        <Link to="/validador-orcamento" className="ml-auto underline text-sm">
          voltar
        </Link>
      </div>

      {loading && <div className="card">Aguardando término do job…</div>}
      {err && <div className="card text-red-600">Erro: {err}</div>}

      {job && (
        <div className="card text-left">
          <div><b>Status:</b> {job.status}</div>
          <div><b>API:</b> {API_BASE_URL}</div>
        </div>
      )}

      {data && (
        <div className="card text-left">
          <div className="mb-2 flex gap-2">
            <button className="btn-ghost small" onClick={copyJson} disabled={!pretty}>Copiar JSON</button>
            <button className="btn-ghost small" onClick={downloadJson} disabled={!pretty}>Baixar JSON</button>
          </div>
          <pre className="text-xs overflow-auto" style={{ maxHeight: 520 }}>
{pretty}
          </pre>
        </div>
      )}
    </main>
  );
}
