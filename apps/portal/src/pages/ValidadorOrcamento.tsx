import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getRecent, pushRecent, clearRecent } from "../lib/recentJobs";

type Op = "precos_manual" | "precos_auto" | "estrutura";
type JobResp = { id: string; status: string };

export default function ValidadorOrcamentoPage() {
  const nav = useNavigate();
  const BASE = useMemo(() => {
    const env = (import.meta.env.VITE_API_BASE_URL ?? "").trim();
    return env !== "" ? env : `${location.protocol}//${location.hostname}:8001`;
  }, []);

  const [op, setOp] = useState<Op>("precos_manual");
  const [orc, setOrc] = useState("/app/data/ORÇAMENTO - ACIONAMENTO 01 - REV 05 final.xlsx");
  const [ref, setRef] = useState("/app/data/SINAPI_2025_06.xlsx");
  const [refType, setRefType] = useState<"SINAPI" | "SUDECAP">("SINAPI");
  const [banco, setBanco] = useState<"SINAPI" | "SUDECAP">("SINAPI");
  const [tol, setTol] = useState(0);
  const [out, setOut] = useState("/app/output/cruzamento_precos_sinapi.json");
  const [outDir, setOutDir] = useState("/app/output");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queue, setQueue] = useState<string[]>([]);
  const [health, setHealth] = useState<string>("…");

  useEffect(() => {
    // health
    fetch(`${BASE}/health`)
      .then(r => r.json())
      .then(_ => setHealth("online"))
      .catch(() => setHealth("offline"));

    // carregar fila local ao montar
    const load = () => setQueue(getRecent().map(j => j.id));
    load();

    // escutar atualizações disparadas pelo helper
    const onUpd = () => load();
    window.addEventListener('recent-jobs-updated', onUpd as any);

    // sincronizar entre abas
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'agepar:recent-jobs') load();
    };
    window.addEventListener('storage', onStorage);

    return () => {
      window.removeEventListener('recent-jobs-updated', onUpd as any);
      window.removeEventListener('storage', onStorage);
    };
  }, [BASE]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true); setError(null);
    try {
      let payload: any;
      if (op === "precos_manual") {
        payload = { op, orc, ref, ref_type: refType, banco, tol_rel: Number(tol), out };
      } else if (op === "precos_auto") {
        payload = { op, orc, tol_rel: Number(tol), out_dir: outDir };
      } else {
        payload = { op, orc, banco_a: banco, base: ref, base_type: refType, out };
      }
      const resp = await fetch(`${BASE}/jobs`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!resp.ok) throw new Error(await resp.text());
      const j = await resp.json() as JobResp;

      // persiste e reflete a fila local
      pushRecent(j.id);
      setQueue(getRecent().map(x => x.id));
      // nav(`/jobs/${j.id}`);
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="p-6 max-w-5xl mx-auto space-y-6">
      <header className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Validador de Orçamento</h1>
        <span className={`text-sm px-2 py-1 rounded ${health === 'online' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
          {health}
        </span>
      </header>

      <form className="form-card space-y-5" onSubmit={submit}>
        <div className="grid md:grid-cols-2 gap-4">
          <label className="field">
            <span className="label">Operação</span>
            <select value={op} onChange={e => setOp(e.target.value as Op)}>
              <option value="precos_manual">Preço (manual)</option>
              <option value="precos_auto">Preço (automático)</option>
              <option value="estrutura">Estrutura</option>
            </select>
          </label>
          <label className="field">
            <span className="label">Banco</span>
            <select value={banco} onChange={e => setBanco(e.target.value as any)}>
              <option value="SINAPI">SINAPI</option>
              <option value="SUDECAP">SUDECAP</option>
            </select>
          </label>
        </div>

        <label className="field">
          <span className="label">Arquivo Orçamento (no container)</span>
          <input value={orc} onChange={e => setOrc(e.target.value)} placeholder="/app/data/..." />
        </label>

        {op !== "precos_auto" && (
          <div className="grid md:grid-cols-2 gap-4">
            <label className="field">
              <span className="label">Arquivo Referência (no container)</span>
              <input value={ref} onChange={e => setRef(e.target.value)} placeholder="/app/data/..." />
            </label>
            <label className="field">
              <span className="label">Tipo da Referência</span>
              <select value={refType} onChange={e => setRefType(e.target.value as any)}>
                <option value="SINAPI">SINAPI</option>
                <option value="SUDECAP">SUDECAP</option>
              </select>
            </label>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-4">
          <label className="field">
            <span className="label">Tolerância Relativa</span>
            <input type="number" step="0.01" value={tol} onChange={e => setTol(Number(e.target.value))} />
          </label>

          {op === "precos_auto" ? (
            <label className="field">
              <span className="label">Pasta de Saída</span>
              <input value={outDir} onChange={e => setOutDir(e.target.value)} placeholder="/app/output" />
            </label>
          ) : (
            <label className="field">
              <span className="label">Arquivo de Saída</span>
              <input value={out} onChange={e => setOut(e.target.value)} placeholder="/app/output/..." />
            </label>
          )}
        </div>

        {error && <p className="text-red-600 text-sm">Erro: {error}</p>}
        <button className="btn-primary" disabled={submitting}>{submitting ? "Enviando..." : "Criar Job"}</button>

        <p className="text-xs text-[var(--muted)]">
          Obs (dev): nesta fase os caminhos são do container do worker (ex.: <code>/app/data</code>, <code>/app/output</code>).
          Depois trocaremos por upload (MinIO) e link de resultado.
        </p>
      </form>

      <section className="form-card">
        <div className="flex items-center mb-2 gap-2">
          <h2 className="text-lg font-medium">Fila local (últimos envios)</h2>
          <button type="button" className="btn-ghost small ml-auto" onClick={() => { clearRecent(); setQueue([]); }}>
            Limpar
          </button>
        </div>
        {queue.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Sem envios por enquanto.</p>
        ) : (
          <ul className="list-disc pl-5 space-y-1">
            {queue.map(id => (
              <li key={id}>
                <a className="text-blue-600 underline" onClick={() => nav(`/jobs/${id}`)}>{id}</a>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
