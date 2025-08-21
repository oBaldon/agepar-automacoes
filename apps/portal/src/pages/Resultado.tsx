// apps/portal/src/pages/Resultado.tsx
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { API_BASE_URL, getEstrutura, getPrecos } from "../lib/api";

type Kind = "precos" | "estrutura";

export default function Resultado() {
  const [params] = useSearchParams();
  const kind = (params.get("kind") as Kind) || "precos";

  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const pretty = useMemo(() => (data ? JSON.stringify(data, null, 2) : ""), [data]);

  useEffect(() => {
    let stop = false;
    async function load() {
      try {
        setErr(null);
        setLoading(true);
        const result = kind === "precos" ? await getPrecos() : await getEstrutura();
        if (!stop) setData(result);
      } catch (e: any) {
        if (!stop) setErr(e?.message ?? "Erro ao carregar resultado");
      } finally {
        if (!stop) setLoading(false);
      }
    }
    load();
    return () => { stop = true; };
  }, [kind]);

  const copyJson = async () => {
    try {
      await navigator.clipboard.writeText(pretty);
      alert("JSON copiado para a área de transferência.");
    } catch {
      alert("Falha ao copiar.");
    }
  };

  const downloadJson = () => {
    const blob = new Blob([pretty], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `resultado_${kind}.json`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="p-6 max-w-5xl mx-auto space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold">Resultado</h1>
        <code className="text-xs opacity-70">{API_BASE_URL}</code>
        <span className="ml-2 text-xs px-2 py-0.5 rounded bg-gray-100">{kind}</span>
        <Link to="/validador-orcamento" className="ml-auto underline text-sm">voltar</Link>
      </div>

      {loading && <div className="card">Carregando…</div>}
      {err && <div className="card text-red-600">Erro: {err}</div>}

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
