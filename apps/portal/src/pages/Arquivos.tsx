// apps/portal/src/pages/Arquivos.tsx
import { useCallback, useEffect, useMemo, useState } from "react";
import { listFiles, type FilesResponse } from "../lib/api";

export default function Arquivos() {
  const [files, setFiles] = useState<FilesResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchFiles = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const resp = await listFiles();
      setFiles(resp);
    } catch (e: any) {
      setErr(e?.message ?? "Falha ao listar arquivos.");
      setFiles(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const items = useMemo(() => {
    if (!files) return [];
    // Garante mais recentes primeiro mesmo que a API mude
    return [...files.files].sort((a, b) => (b.mtime ?? 0) - (a.mtime ?? 0));
  }, [files]);

  return (
    <main className="p-6 max-w-4xl mx-auto space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold">Arquivos no /output</h1>
        <button className="btn-ghost small" onClick={fetchFiles} disabled={loading}>
          {loading ? "Atualizando…" : "Atualizar"}
        </button>
      </div>

      {files && (
        <p className="text-xs text-[var(--muted)]">
          Pasta: <code>{files.output_dir}</code>
          {typeof files.count === "number" && <> • {files.count} arquivo(s)</>}
        </p>
      )}

      {err && <div className="card text-red-600">Erro: {err}</div>}
      {loading && <div className="card">Carregando…</div>}

      {!loading && files && items.length === 0 && (
        <div className="card text-sm text-[var(--muted)]">
          Nenhum JSON em {files.output_dir}.
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="card">
          <ul className="text-sm space-y-1">
            {items.map((f) => (
              <li key={f.path} className="flex items-center gap-2">
                <code className="opacity-80">{f.name}</code>
                <span className="text-xs opacity-60">
                  {f.size_human ?? `${f.size} bytes`} •{" "}
                  {f.mtime_iso ?? new Date((f.mtime ?? 0) * 1000).toISOString()}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </main>
  );
}
