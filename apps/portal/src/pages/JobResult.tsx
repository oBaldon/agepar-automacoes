import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { API_BASE_URL, getJob, getJobResult, type Job } from "../lib/api";

export default function JobResult(){
  const { id = "" } = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const pretty = useMemo(() => (data ? JSON.stringify(data, null, 2) : ""), [data]);

  // utilitários
  const copyJson = async () => {
    try {
      await navigator.clipboard.writeText(pretty);
      alert("JSON copiado para a área de transferência.");
    } catch (e) {
      alert("Falha ao copiar.");
    }
  };

  const downloadJson = () => {
    const blob = new Blob([pretty], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `job_${id}.json`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  };

  // polling do status + fetch do resultado quando terminar
  useEffect(() => {
    if (!id) return;
    let timer: number | undefined;
    let stop = false;

    async function tick() {
      try {
        setErr(null);
        const j = await getJob(id);
        setJob(j);

        if (j.status === "finished") {
          const result = await getJobResult(id);
          setData(result);
          setLoading(false);
          return; // para de pollar
        }

        if (j.status === "failed") {
          setLoading(false);
          setErr("Job falhou. Verifique logs do worker.");
          return;
        }
      } catch (e: any) {
        setErr(e?.message ?? "Erro ao consultar job");
      }
      if (!stop) {
        timer = window.setTimeout(tick, 2000);
      }
    }

    setLoading(true);
    tick();

    return () => {
      stop = true;
      if (timer) window.clearTimeout(timer);
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
            <button className="btn-ghost small" onClick={copyJson}>Copiar</button>
            <button className="btn-ghost small" onClick={downloadJson}>Baixar</button>
          </div>
          <pre className="text-xs overflow-auto" style={{ maxHeight: 500 }}>
{pretty}
          </pre>
        </div>
      )}
    </main>
  );
}
