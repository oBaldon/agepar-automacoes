// apps/portal/src/pages/ValidadorOrcamento.tsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  API_BASE_URL,
  health as apiHealth,
  createJob,
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

export default function ValidadorOrcamentoPage() {
  const nav = useNavigate();

  // health
  const [health, setHealth] = useState<"online" | "offline" | "…">("…");
  useEffect(() => {
    apiHealth()
      .then(() => setHealth("online"))
      .catch(() => setHealth("offline"));
  }, []);

  // operação e campos
  const [op, setOp] = useState<Op>("precos_auto");
  const [orc, setOrc] = useState("data/orcamento.xlsx");

  // PREÇOS
  const [sudecap, setSudecap] = useState("data/sudecap_preco.xls");
  const [sinapi, setSinapi] = useState("data/sinapi_ccd.xlsx");

  // ESTRUTURA
  const [sudecapEstr, setSudecapEstr] = useState("data/sudecap_comp.xls");
  const [sinapiEstr, setSinapiEstr] = useState("data/sinapi_ccd.xlsx");

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
        throw new Error("Preencha Orçamento e Pasta de saída.");
      }

      let jobPayload: PrecosAutoPayload | EstruturaAutoPayload;

      if (op === "precos_auto") {
        if (!sudecap || !sinapi) throw new Error("Preencha SUDECAP e SINAPI (preços).");
        jobPayload = {
          op,
          orc: orc.trim(),
          sudecap: sudecap.trim(),
          sinapi: sinapi.trim(),
          out_dir: outDir.trim(),
          tol_rel: Math.max(0, Number.isFinite(tolRel) ? tolRel : 0.05),
          comparar_desc: compararDesc,
        };
      } else {
        if (!sudecapEstr || !sinapiEstr) throw new Error("Preencha SUDECAP e SINAPI (estrutura).");
        jobPayload = {
          op,
          orc: orc.trim(),
          sudecap: sudecapEstr.trim(),
          sinapi: sinapiEstr.trim(),
          out_dir: outDir.trim(),
        };
      }

      const job: Job = await createJob(jobPayload as any);
      pushRecent(job.id); // registra localmente
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
            <input value={outDir} onChange={(e) => setOutDir(e.target.value)} placeholder="output" />
          </label>
        </div>

        <label className="field">
          <span className="label">Arquivo do Orçamento (no worker)</span>
          <input value={orc} onChange={(e) => setOrc(e.target.value)} placeholder="data/orcamento.xlsx" />
        </label>

        {op === "precos_auto" ? (
          <>
            <div className="grid md:grid-cols-2 gap-4">
              <label className="field">
                <span className="label">SUDECAP (preços)</span>
                <input
                  value={sudecap}
                  onChange={(e) => setSudecap(e.target.value)}
                  placeholder="data/sudecap_preco.xls"
                />
              </label>
              <label className="field">
                <span className="label">SINAPI (preços)</span>
                <input
                  value={sinapi}
                  onChange={(e) => setSinapi(e.target.value)}
                  placeholder="data/sinapi_ccd.xlsx"
                />
              </label>
            </div>

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
              <label className="field">
                <span className="label">SUDECAP (estrutura)</span>
                <input
                  value={sudecapEstr}
                  onChange={(e) => setSudecapEstr(e.target.value)}
                  placeholder="data/sudecap_comp.xls"
                />
              </label>
              <label className="field">
                <span className="label">SINAPI (estrutura)</span>
                <input
                  value={sinapiEstr}
                  onChange={(e) => setSinapiEstr(e.target.value)}
                  placeholder="data/sinapi_estrutura.xlsx"
                />
              </label>
            </div>
          </>
        )}

        {err && <p className="text-red-600 text-sm">Erro: {err}</p>}

        <div className="flex gap-3">
          <button className="btn-primary" disabled={submitting || health !== "online"}>
            {submitting ? "Enviando..." : "Criar Job"}
          </button>
        </div>

        <p className="text-xs text-[var(--muted)]">
          Dica: os caminhos são relativos ao <code>/app</code> do container do <b>worker</b>. Exemplos:{" "}
          <code>data/arquivo.xlsx</code> e <code>output</code>.
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
          <code>VITE_LINK_SINAPI</code>, <code>VITE_LINK_SUDECAP</code>…).
        </p>
      </section>
    </main>
  );
}
