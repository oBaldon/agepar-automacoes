// apps/portal/src/pages/ValidadorOrcamento.tsx
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { health as apiHealth, listFiles, type FilesResponse } from "../lib/api";

export default function ValidadorOrcamentoPage() {
  const BASE = useMemo(() => {
    const env = (import.meta.env.VITE_API_BASE_URL ?? "").trim();
    return env !== "" ? env : `${location.protocol}//${location.hostname}:8001`;
  }, []);

  const [health, setHealth] = useState<string>("…");
  const [files, setFiles] = useState<FilesResponse | null>(null);

  useEffect(() => {
    apiHealth().then(_ => setHealth("online")).catch(() => setHealth("offline"));
    listFiles().then(setFiles).catch(() => setFiles(null));
  }, []);

  return (
    <main className="p-6 max-w-5xl mx-auto space-y-6">
      <header className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Validador de Orçamento</h1>
        <code className="text-xs opacity-70">{BASE}</code>
        <span className={`text-sm px-2 py-1 rounded ${health === 'online' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
          {health}
        </span>
      </header>

      <div className="form-card space-y-3">
        <p className="text-sm text-[var(--muted)]">
          Esta interface apenas lê os JSONs gerados pelo worker em <code>/app/output</code>.
        </p>
        <div className="flex gap-3">
          <Link to="/resultado?kind=precos" className="btn-primary">Ver Preços</Link>
          <Link to="/resultado?kind=estrutura" className="btn-primary">Ver Estrutura</Link>
        </div>
      </div>

      <section className="form-card">
        <h2 className="text-lg font-medium mb-2">Arquivos disponíveis</h2>
        {!files ? (
          <p className="text-sm text-[var(--muted)]">Não foi possível listar /files.</p>
        ) : files.files.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Nenhum JSON encontrado em {files.output_dir}.</p>
        ) : (
          <ul className="text-sm space-y-1">
            {files.files.map(f => (
              <li key={f.path} className="flex gap-2 items-center">
                <code className="opacity-70">{f.name}</code>
                <span className="text-xs opacity-60">({f.size} bytes)</span>
                {f.name === "precos.json" && <Link to="/resultado?kind=precos" className="underline text-blue-600 ml-2">abrir</Link>}
                {f.name === "estrutura.json" && <Link to="/resultado?kind=estrutura" className="underline text-blue-600 ml-2">abrir</Link>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
