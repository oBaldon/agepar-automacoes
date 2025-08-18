export type StoredJob = {
  id: string;
  op: "precos_manual" | "precos_auto" | "estrutura";
  label?: string;
  createdAt: number;
};

const KEY = "agepar.jobs";

function read(): StoredJob[] {
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); }
  catch { return []; }
}
function write(v: StoredJob[]) {
  localStorage.setItem(KEY, JSON.stringify(v));
}

export const JobsStorage = {
  all(): StoredJob[] { return read(); },
  push(job: StoredJob) { const arr = read(); arr.unshift(job); write(arr.slice(0,50)); },
  remove(id: string) { write(read().filter(j => j.id !== id)); },
  clear() { write([]); },
};
