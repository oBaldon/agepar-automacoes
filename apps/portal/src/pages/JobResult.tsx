// apps/portal/src/pages/JobResult.tsx
import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { API_BASE_URL, getJob, getJobResult, type Job } from "../lib/api";
import { pushRecent } from "../lib/recentJobs";

// ---------- utils ----------
type Row = Record<string, any>;

function isObject(v: unknown): v is Record<string, any> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

function flattenRow(input: any, prefix = ""): Row {
  const out: Row = {};
  const pre = prefix ? prefix + "." : "";
  if (!isObject(input)) return { [prefix || "value"]: input };

  for (const [k, v] of Object.entries(input)) {
    const key = pre + k;
    if (Array.isArray(v)) {
      // junta arrays simples; se for array de objetos, serializa curto
      if (v.every((x) => !isObject(x))) {
        out[key] = v.join(", ");
      } else {
        out[key] = JSON.stringify(v);
      }
    } else if (isObject(v)) {
      Object.assign(out, flattenRow(v, key));
    } else {
      out[key] = v;
    }
  }
  return out;
}

function autoDatasets(data: any): { name: string; rows: Row[] }[] {
  if (!data) return [];
  // Caso o backend retorne um array na raiz
  if (Array.isArray(data) && data.length && isObject(data[0])) {
    return [{ name: "resultado", rows: data.map((r) => flattenRow(r)) }];
  }
  // Caso padrão: procurar chaves com arrays de objetos
  if (isObject(data)) {
    const out: { name: string; rows: Row[] }[] = [];
    for (const [key, val] of Object.entries(data)) {
      if (Array.isArray(val) && val.length && isObject(val[0])) {
        out.push({ name: key, rows: val.map((r) => flattenRow(r)) });
      }
    }
    return out;
  }
  return [];
}

function collectColumns(rows: Row[]): string[] {
  const set = new Set<string>();
  for (const r of rows) for (const k of Object.keys(r)) set.add(k);
  // Colunas “mais comuns” primeiro, se existirem
  const preferred = [
    "codigo",
    "codigo_base",
    "a_banco",
    "a_desc",
    "a_valor",
    "sinapi.valor",
    "sinapi.ok",
    "sudecap.valor",
    "sudecap.ok",
    "dif_abs",
    "dif_rel",
    "dir",
    "motivos",
  ];
  const rest = [...set].filter((c) => !preferred.includes(c));
  return [...preferred.filter((c) => set.has(c)), ...rest].slice(0, 80);
}

function formatCell(col: string, val: any) {
  if (val === null || val === undefined) return "";
  if (typeof val === "number") {
    if (col.toLowerCase().includes("dif_rel")) {
      return (val * 100).toLocaleString("pt-BR", { maximumFractionDigits: 3 }) + "%";
    }
    return val.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
  }
  if (typeof val === "boolean") return val ? "true" : "false";
  return String(val);
}

function toCsv(rows: Row[], cols: string[]): string {
  const escape = (s: any) =>
    `"${String(s).replaceAll(`"`, `""`).replaceAll(`\n`, " ").replaceAll(`\r`, "")}"`;
  const head = cols.map(escape).join(",");
  const body = rows.map((r) => cols.map((c) => escape(r[c] ?? "")).join(",")).join("\n");
  return head + "\n" + body;
}

// ---------- page ----------
export default function JobResult() {
  const { id = "" } = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const pretty = useMemo(() => (data ? JSON.stringify(data, null, 2) : ""), [data]);

  // UI state
  const datasets = useMemo(() => autoDatasets(data), [data]);
  const [activeTab, setActiveTab] = useState(0);
  const [query, setQuery] = useState("");
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const active = datasets[activeTab] || { name: "", rows: [] };
  const allCols = useMemo(() => collectColumns(active.rows), [active]);
  const [copied, setCopied] = useState(false);

  const filtered = useMemo(() => {
    if (!query.trim()) return active.rows;
    const q = query.toLowerCase();
    return active.rows.filter((r) =>
      allCols.some((c) => String(r[c] ?? "").toLowerCase().includes(q))
    );
  }, [active.rows, query, allCols]);

  const sorted = useMemo(() => {
    if (!sortCol) return filtered;
    const arr = [...filtered];
    arr.sort((a, b) => {
      const va = a[sortCol];
      const vb = b[sortCol];
      if (va == null && vb == null) return 0;
      if (va == null) return sortDir === "asc" ? -1 : 1;
      if (vb == null) return sortDir === "asc" ? 1 : -1;
      if (typeof va === "number" && typeof vb === "number") {
        return sortDir === "asc" ? va - vb : vb - va;
      }
      return sortDir === "asc"
        ? String(va).localeCompare(String(vb))
        : String(vb).localeCompare(String(va));
    });
    return arr;
  }, [filtered, sortCol, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const pageRows = useMemo(() => {
    const p = Math.min(page, totalPages);
    const start = (p - 1) * pageSize;
    return sorted.slice(start, start + pageSize);
  }, [sorted, page, pageSize, totalPages]);

  useEffect(() => setPage(1), [activeTab, query, pageSize]);

  async function copyJson() {
    try {
      const text = pretty;
      // Caminho "bonito" quando em contexto seguro
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback compatível com HTTP/intranet
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch (e) {
      console.error(e);
      setErr("Não foi possível copiar. Use o botão Baixar JSON.");
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

  function downloadCsv() {
    const csv = toCsv(sorted, allCols);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${active.name || "resultado"}.csv`;
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
            pushRecent(id); // re-registra pra subir pro topo
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
    <main className="p-6 max-w-7xl mx-auto space-y-4">
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

      {/* Resumo rápido (se existir) */}
      {data?.resumo && (
        <div className="card text-left">
          <h2 className="font-semibold mb-2">Resumo</h2>
          <pre className="text-xs overflow-auto">{JSON.stringify(data.resumo, null, 2)}</pre>
        </div>
      )}

      {/* Abas dos datasets detectados */}
      {!!datasets.length && (
        <div className="card text-left">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {datasets.map((d, i) => (
              <button
                key={d.name}
                className={`btn-ghost small ${i === activeTab ? "border border-neutral-400" : ""}`}
                onClick={() => setActiveTab(i)}
                title={`Ver ${d.name}`}
              >
                {d.name} <span className="opacity-60 ml-1">({d.rows.length})</span>
              </button>
            ))}
            <div className="ml-auto flex items-center gap-2">
              <input
                className="input small w-64"
                placeholder="Filtrar…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <select
                className="input small"
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value))}
                title="Itens por página"
              >
                {[10, 25, 50, 100, 200].map((n) => (
                  <option key={n} value={n}>{n}/página</option>
                ))}
              </select>
              <button className="btn-ghost small" onClick={downloadCsv} disabled={!active.rows.length}>
                Exportar CSV
              </button>
            </div>
          </div>

          {/* Tabela */}
          <div className="data-surface overflow-auto border rounded-xl" style={{ maxHeight: 520 }}>
            <table className="data-table min-w-full text-sm">
              <thead className="sticky top-0 bg-white shadow-sm">
                <tr>
                  {allCols.map((c) => (
                    <th
                      key={c}
                      className="text-left px-3 py-2 whitespace-nowrap cursor-pointer select-none"
                      onClick={() => {
                        if (sortCol === c) {
                          setSortDir((d) => (d === "asc" ? "desc" : "asc"));
                        } else {
                          setSortCol(c);
                          setSortDir("asc");
                        }
                      }}
                    >
                      <div className="flex items-center gap-1">
                        <span className="font-medium">{c}</span>
                        {sortCol === c && <span className="text-xs opacity-60">{sortDir === "asc" ? "▲" : "▼"}</span>}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageRows.length === 0 && (
                  <tr><td className="px-3 py-3 text-center opacity-70" colSpan={allCols.length}>Sem resultados</td></tr>
                )}
                {pageRows.map((r, i) => (
                  <tr key={i} className="odd:bg-neutral-50">
                    {allCols.map((c) => (
                      <td key={c} className="px-3 py-1.5 align-top whitespace-pre-wrap">
                        {formatCell(c, r[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Paginação */}
          <div className="mt-3 flex items-center gap-2">
            <button
              className="btn-ghost small"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              ← Anterior
            </button>
            <div className="text-sm opacity-80">
              Página {page} de {totalPages} — {sorted.length} itens
            </div>
            <button
              className="btn-ghost small"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              Próxima →
            </button>
          </div>
        </div>
      )}

      {/* JSON bruto para debug/baixar */}
      {data && (
        <div className="card text-left">
          <div className="mb-2 flex gap-2">
            <button className="btn-ghost small" onClick={copyJson} disabled={!pretty}>
              {copied ? "Copiado ✓" : "Copiar JSON"}
            </button>

            <button className="btn-ghost small" onClick={downloadJson} disabled={!pretty}>
              Baixar JSON
            </button>
          </div>
          <pre className="text-xs overflow-auto" style={{ maxHeight: 420 }}>
            {pretty}
          </pre>
        </div>
      )}
    </main>
  );
}
