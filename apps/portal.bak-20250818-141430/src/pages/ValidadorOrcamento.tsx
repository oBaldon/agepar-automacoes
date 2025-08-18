import { useState } from "react";
import { createJob, type JobCreate } from "../lib/api";
import { useJobPolling } from "../hooks/useJobPolling";

export default function ValidadorOrcamentoPage() {
  const [op, setOp] = useState<JobCreate["op"]>("precos_manual");

  const [orc, setOrc] = useState<string>("/app/data/ORÇAMENTO - ACIONAMENTO 01 - REV 05 final.xlsx");
  const [ref, setRef] = useState<string>("/app/data/SINAPI_2025_06.xlsx");
  const [refType, setRefType] = useState<"SINAPI" | "SUDECAP">("SINAPI");
  const [banco, setBanco] = useState<"SINAPI" | "SUDECAP">("SINAPI");
  const [tolRel, setTolRel] = useState<number>(0);
  const [out, setOut] = useState<string>("/app/output/cruzamento_precos_sinapi.json");

  const [outDir, setOutDir] = useState<string>("/app/output");
  const [bancoA, setBancoA] = useState<"SINAPI" | "SUDECAP">("SINAPI");
  const [base, setBase] = useState<string>("/app/data/SINAPI_2025_06.xlsx");
  const [baseType, setBaseType] = useState<"SINAPI" | "SUDECAP">("SINAPI");

  const [jobId, setJobId] = useState<string | null>(null);
  const { data: job, error } = useJobPolling(jobId ?? undefined, 1500);
  const [busy, setBusy] = useState(false);
  const [errForm, setErrForm] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrForm(null);
    setBusy(true);
    try {
      let payload: JobCreate;
      if (op === "precos_manual") {
        payload = { op, orc, ref, ref_type: refType, banco, tol_rel: tolRel, out };
      } else if (op === "precos_auto") {
        payload = { op, orc, tol_rel: tolRel, out_dir: outDir };
      } else {
        payload = { op, orc, banco_a: bancoA, base, base_type: baseType, out };
      }
      const created = await createJob(payload);
      setJobId(created.id);
    } catch (e: any) {
      setErrForm(String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-4 space-y-6">
      <h1 className="text-2xl font-semibold">Validador de Orçamento</h1>

      <form onSubmit={onSubmit} className="card space-y-4">
        <div className="grid gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium">Operação</span>
            <select value={op} onChange={(e) => setOp(e.target.value as any)} className="border rounded p-2">
              <option value="precos_manual">Preços (manual)</option>
              <option value="precos_auto">Preços (automático)</option>
              <option value="estrutura">Estrutura</option>
            </select>
          </label>

          {op === "precos_manual" && (
            <>
              <label className="flex flex-col gap-1">
                <span className="text-sm font-medium">Orçamento (path no container)</span>
                <input value={orc} onChange={(e) => setOrc(e.target.value)} className="border rounded p-2" />
              </label>
              <div className="grid sm:grid-cols-3 gap-3">
                <label className="flex flex-col gap-1 sm:col-span-2">
                  <span className="text-sm font-medium">Referência</span>
                  <input value={ref} onChange={(e) => setRef(e.target.value)} className="border rounded p-2" />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium">Ref. Type</span>
                  <select value={refType} onChange={(e) => setRefType(e.target.value as any)} className="border rounded p-2">
                    <option value="SINAPI">SINAPI</option>
                    <option value="SUDECAP">SUDECAP</option>
                  </select>
                </label>
              </div>
              <div className="grid sm:grid-cols-3 gap-3">
                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium">Banco</span>
                  <select value={banco} onChange={(e) => setBanco(e.target.value as any)} className="border rounded p-2">
                    <option value="SINAPI">SINAPI</option>
                    <option value="SUDECAP">SUDECAP</option>
                  </select>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium">Tolerância Relativa</span>
                  <input type="number" step="0.01" value={tolRel} onChange={(e) => setTolRel(parseFloat(e.target.value))} className="border rounded p-2" />
                </label>
                <label className="flex flex-col gap-1 sm:col-span-1">
                  <span className="text-sm font-medium">Saída (JSON)</span>
                  <input value={out} onChange={(e) => setOut(e.target.value)} className="border rounded p-2" />
                </label>
              </div>
            </>
          )}

          {op === "precos_auto" && (
            <>
              <label className="flex flex-col gap-1">
                <span className="text-sm font-medium">Orçamento</span>
                <input value={orc} onChange={(e) => setOrc(e.target.value)} className="border rounded p-2" />
              </label>
              <div className="grid sm:grid-cols-2 gap-3">
                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium">Tolerância Relativa</span>
                  <input type="number" step="0.01" value={tolRel} onChange={(e) => setTolRel(parseFloat(e.target.value))} className="border rounded p-2" />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium">Diretório de saída</span>
                  <input value={outDir} onChange={(e) => setOutDir(e.target.value)} className="border rounded p-2" />
                </label>
              </div>
            </>
          )}

          {op === "estrutura" && (
            <>
              <label className="flex flex-col gap-1">
                <span className="text-sm font-medium">Orçamento</span>
                <input value={orc} onChange={(e) => setOrc(e.target.value)} className="border rounded p-2" />
              </label>
              <div className="grid sm:grid-cols-3 gap-3">
                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium">Banco A</span>
                  <select value={bancoA} onChange={(e) => setBancoA(e.target.value as any)} className="border rounded p-2">
                    <option value="SINAPI">SINAPI</option>
                    <option value="SUDECAP">SUDECAP</option>
                  </select>
                </label>
                <label className="flex flex-col gap-1 sm:col-span-2">
                  <span className="text-sm font-medium">Base</span>
                  <input value={base} onChange={(e) => setBase(e.target.value)} className="border rounded p-2" />
                </label>
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium">Base Type</span>
                  <select value={baseType} onChange={(e) => setBaseType(e.target.value as any)} className="border rounded p-2">
                    <option value="SINAPI">SINAPI</option>
                    <option value="SUDECAP">SUDECAP</option>
                  </select>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium">Saída (JSON)</span>
                  <input value={out} onChange={(e) => setOut(e.target.value)} className="border rounded p-2" />
                </label>
              </div>
            </>
          )}
        </div>

        {errForm && <p className="text-red-600 text-sm">{errForm}</p>}

        <button
          disabled={busy}
          className="btn-primary"
        >
          {busy ? "Enviando..." : "Enviar"}
        </button>
      </form>

      {jobId && (
        <div className="card">
          <p><b>Job:</b> {jobId}</p>
          <p><b>Status:</b> {job?.status ?? "..."}</p>
          {"artifact" in (job ?? {}) && job?.artifact && (
            <pre className="text-xs bg-gray-100 p-2 rounded mt-2 overflow-auto">
{JSON.stringify(job.artifact, null, 2)}
            </pre>
          )}
          {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
        </div>
      )}

      <p className="text-xs text-gray-500">
        <b>Obs (dev):</b> nesta fase os caminhos são do <i>container</i> do worker (ex.: <code>/app/data</code> e <code>/app/output</code>). No Dia 4 vamos trocar por upload (MinIO) e link do resultado.
      </p>
    </div>
  );
}
