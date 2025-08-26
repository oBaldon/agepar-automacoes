// apps/portal/src/pages/ValidadorOrcamento.tsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  API_BASE_URL,
  health as apiHealth,
  createJob,
  uploadFile,                // <<< novo
  type Job,
  type PrecosAutoPayload,
  type EstruturaAutoPayload,
} from "../lib/api";
import { pushRecent } from "../lib/recentJobs";

type Op = "precos_auto" | "estrutura_auto";

// Links úteis configuráveis via .env (Vite)
const LINKS_UTEIS: Array<{ label: string; url?: string; hint?: string }> = [
  {
    label: "SINAPI – relatórios mensais",
    url: import.meta.env.VITE_LINK_SINAPI as string | undefined,
    hint: "Defina VITE_LINK_SINAPI no .env",
  },
  {
    label: "SUDECAP – tabelas de preços",
    url: import.meta.env.VITE_LINK_SUDECAP_PRECO as string | undefined,
    hint: "Defina VITE_LINK_SUDECAP_PRECO no .env",
  },
  {
    label: "SUDECAP – composições de serviços",
    url: import.meta.env.VITE_API_SUDECAP_COMPOSICAO as string | undefined,
    hint: "Defina VITE_API_SUDECAP_COMPOSICAO no .env",
  },
  {
    label: "SECID – custos de edificações",
    url: import.meta.env.VITE_LINK_SECID as string | undefined,
    hint: "Defina VITE_LINK_SECID no .env",
  },
  {
    label: "CPOS/CDHU – catálogo",
    url: import.meta.env.VITE_LINK_CPOS as string | undefined,
    hint: "Defina VITE_LINK_CPOS no .env",
  },
  {
    label: "SBC / TCPO",
    url: import.meta.env.VITE_LINK_SBC as string | undefined,
    hint: "Defina VITE_LINK_SBC no .env",
  },
];

// --- Mini componente de upload (local ao arquivo) ---
function UploadField(props: {
  label: string;
  value: string;                              // path_for_job atual (ex.: data/uploads/jobX/arquivo.xlsx)
  onUploaded: (pathForJob: string) => void;   // callback com o path salvo
  subdir: string;                              // subpasta de upload (ex.: "uploads/job_...") 
  accept?: string;
  disabled?: boolean;
}) {
  const { label, value, onUploaded, subdir, accept, disabled } = props;
  const [status, setStatus] = useState<"idle" | "uploading" | "ok" | "error">("idle");
  const [msg, setMsg] = useState<string | null>(null);

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setStatus("uploading");
    setMsg(null);
    try {
      const resp = await uploadFile(file, subdir);
      onUploaded(resp.path_for_job); // ex.: "data/uploads/job1/arquivo.xlsx"
      setStatus("ok");
      setMsg(`${resp.filename} enviado (${resp.bytes} bytes)`);
    } catch (err: any) {
      setStatus("error");
      setMsg(err?.message ?? "Falha no upload");
    }
  }

  return (
    <label className="field">
      <span className="label">{label}</span>
      <div className="flex flex-col gap-2">
        <input type="file" onChange={handleChange} accept={accept} disabled={disabled} />
        {value ? (
          <code className="text-xs break-all">{value}</code>
        ) : (
          <span className="text-xs opacity-70">Selecione um arquivo para enviar…</span>
        )}
        {status === "uploading" && <span className="text-xs text-blue-600">Enviando…</span>}
        {status === "ok" && <span className="text-xs text-green-700">{msg}</span>}
        {status === "error" && <span className="text-xs text-red-600">{msg}</span>}
      </div>
    </label>
  );
}

export default function ValidadorOrcamentoPage() {
  const nav = useNavigate();

  // health
  const [health, setHealth] = useState<"online" | "offline" | "…">("…");
  useEffect(() => {
    apiHealth()
      .then(() => setHealth("online"))
      .catch(() => setHealth("offline"));
  }, []);

  // operação
  const [op, setOp] = useState<Op>("precos_auto");

  // subpasta de upload única por sessão (facilita rastreio)
  const uploadSubdir = useMemo(() => {
    const pad = (n: number) => String(n).padStart(2, "0");
    const d = new Date();
    const stamp = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
    return `uploads/job_${stamp}`;
  }, []);

  // caminhos (path_for_job) retornados pelo upload
  const [orc, setOrc] = useState<string>(""); // comum
  // PREÇOS
  const [sudecap, setSudecap] = useState<string>("");
  const [sinapi, setSinapi] = useState<string>("");
  const [secid, setSecid] = useState<string>("");
  // ESTRUTURA
  const [sudecapEstr, setSudecapEstr] = useState<string>("");
  const [sinapiEstr, setSinapiEstr] = useState<string>("");
  const [secidEstr, setSecidEstr] = useState<string>("");

  // comuns
  const [outDir, setOutDir] = useState("output");

  // apenas PREÇOS
  const [tolRel, setTolRel] = useState<number>(0.05);
  const [compararDesc, setCompararDesc] = useState<boolean>(true);

  // ui state
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const baseShown = useMemo(() => API_BASE_URL, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErr(null);
    try {
      if (!orc || !outDir) {
        throw new Error("Envie o arquivo do Orçamento e informe a pasta de saída.");
      }

      let jobPayload: PrecosAutoPayload | EstruturaAutoPayload;

      if (op === "precos_auto") {
        if (!sudecap || !sinapi || !secid) {
          throw new Error("Envie SUDECAP, SINAPI e SECID (preços).");
        }
        jobPayload = {
          op,
          orc: orc.trim(),
          sudecap: sudecap.trim(),
          sinapi: sinapi.trim(),
          secid: secid.trim(),
          out_dir: outDir.trim(),
          tol_rel: Math.max(0, Number.isFinite(tolRel) ? tolRel : 0.05),
          comparar_desc: compararDesc,
        };
      } else {
        if (!sudecapEstr || !sinapiEstr || !secidEstr) {
          throw new Error("Envie SUDECAP, SINAPI e SECID (estrutura).");
        }
        jobPayload = {
          op,
          orc: orc.trim(),
          sudecap: sudecapEstr.trim(),
          sinapi: sinapiEstr.trim(),
          secid: secidEstr.trim(),
          out_dir: outDir.trim(),
        };
      }

      const job: Job = await createJob(jobPayload as any);
      pushRecent(job.id);
      nav(`/jobs/${job.id}`);
    } catch (e: any) {
      setErr(e?.message ?? "Falha ao criar job.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="p-6 max-w-5xl mx-auto space-y-6">
      <header className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Validador de Orçamento</h1>
        <code className="text-xs opacity-70">{baseShown}</code>
        <span
          className={`text-sm px-2 py-1 rounded ${
            health === "online" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
          }`}
        >
          {health}
        </span>
      </header>

      <form className="form-card space-y-5" onSubmit={onSubmit}>
        <div className="grid md:grid-cols-2 gap-4">
          <label className="field">
            <span className="label">Operação</span>
            <select value={op} onChange={(e) => setOp(e.target.value as Op)}>
              <option value="precos_auto">Preços (automático)</option>
              <option value="estrutura_auto">Estrutura (automático)</option>
            </select>
          </label>

          <label className="field">
            <span className="label">Pasta de saída</span>
            <input
              value={outDir}
              onChange={(e) => setOutDir(e.target.value)}
              placeholder="output"
            />
            <span className="text-xs opacity-70">Os resultados (JSON) serão salvos nesta pasta no worker.</span>
          </label>
        </div>

        {/* Upload comum: Orçamento */}
        <UploadField
          label="Orçamento (.xlsx)"
          value={orc}
          onUploaded={setOrc}
          subdir={uploadSubdir}
          accept=".xlsx,.xls"
          disabled={submitting || health !== "online"}
        />

        {op === "precos_auto" ? (
          <>
            <div className="grid md:grid-cols-2 gap-4">
              <UploadField
                label="SUDECAP (preços)"
                value={sudecap}
                onUploaded={setSudecap}
                subdir={uploadSubdir}
                accept=".xlsx,.xls"
                disabled={submitting || health !== "online"}
              />
              <UploadField
                label="SINAPI (preços)"
                value={sinapi}
                onUploaded={setSinapi}
                subdir={uploadSubdir}
                accept=".xlsx,.xls"
                disabled={submitting || health !== "online"}
              />
            </div>

            <UploadField
              label="SECID (preços)"
              value={secid}
              onUploaded={setSecid}
              subdir={uploadSubdir}
              accept=".xlsx,.xls"
              disabled={submitting || health !== "online"}
            />

            <div className="grid md:grid-cols-2 gap-4">
              <label className="field">
                <span className="label">Tolerância relativa</span>
                <input
                  type="number"
                  step="0.001"
                  min="0"
                  value={Number.isFinite(tolRel) ? tolRel : 0}
                  onChange={(e) => setTolRel(parseFloat(e.target.value))}
                />
              </label>
              <label className="field">
                <span className="label">Comparar descrições</span>
                <select
                  value={String(compararDesc)}
                  onChange={(e) => setCompararDesc(e.target.value === "true")}
                >
                  <option value="true">Sim</option>
                  <option value="false">Não</option>
                </select>
              </label>
            </div>
          </>
        ) : (
          <>
            <div className="grid md:grid-cols-2 gap-4">
              <UploadField
                label="SUDECAP (estrutura)"
                value={sudecapEstr}
                onUploaded={setSudecapEstr}
                subdir={uploadSubdir}
                accept=".xlsx,.xls"
                disabled={submitting || health !== "online"}
              />
              <UploadField
                label="SINAPI (estrutura)"
                value={sinapiEstr}
                onUploaded={setSinapiEstr}
                subdir={uploadSubdir}
                accept=".xlsx,.xls"
                disabled={submitting || health !== "online"}
              />
            </div>

            <UploadField
              label="SECID (estrutura)"
              value={secidEstr}
              onUploaded={setSecidEstr}
              subdir={uploadSubdir}
              accept=".xlsx,.xls"
              disabled={submitting || health !== "online"}
            />
          </>
        )}

        {err && <p className="text-red-600 text-sm">Erro: {err}</p>}

        <div className="flex gap-3">
          <button className="btn-primary" disabled={submitting || health !== "online"}>
            {submitting ? "Enviando..." : "Criar Job"}
          </button>
        </div>

        <p className="text-xs text-[var(--muted)]">
          Os arquivos são enviados para <code>/app/data/{uploadSubdir}</code> (no worker),
          e os caminhos acima (ex.: <code>data/…</code>) são usados diretamente no job.
        </p>
      </form>

      {/* Bloco de links úteis */}
      <section className="form-card">
        <h2 className="text-lg font-medium mb-2">Links úteis</h2>
        <ul className="list-disc ml-5 space-y-1 text-sm">
          {LINKS_UTEIS.map(({ label, url, hint }) => (
            <li key={label}>
              {url ? (
                <a href={url} target="_blank" rel="noreferrer" className="text-blue-600 underline">
                  {label}
                </a>
              ) : (
                <span className="opacity-70">{label}</span>
              )}
              {!url && hint && <span className="ml-2 text-xs opacity-60">({hint})</span>}
            </li>
          ))}
        </ul>
        <p className="text-xs text-[var(--muted)] mt-2">
          Configure os endereços no arquivo <code>.env</code> do front-end (ex.:{" "}
          <code>VITE_LINK_SINAPI</code>, <code>VITE_LINK_SUDECAP</code>, <code>VITE_LINK_SECID</code>…).
        </p>
      </section>
    </main>
  );
}
