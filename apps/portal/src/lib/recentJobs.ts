// apps/portal/src/lib/recentJobs.ts
export type RecentJob = { id: string; ts: number };

export const RECENT_JOBS_STORAGE_KEY = "agepar:recent-jobs";
export const RECENT_JOBS_EVENT = "recent-jobs-updated";
const MAX_ITEMS = 20;

function hasStorage(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const k = "__test_ls__";
    window.localStorage.setItem(k, "1");
    window.localStorage.removeItem(k);
    return true;
  } catch {
    return false;
  }
}

function safeParse(json: string | null): RecentJob[] {
  if (!json) return [];
  try {
    const arr = JSON.parse(json) as any[];
    if (!Array.isArray(arr)) return [];
    return arr
      .map((x) => {
        const id = String(x?.id ?? "").trim();
        const ts = Number(x?.ts);
        return { id, ts: Number.isFinite(ts) ? ts : Date.now() };
      })
      .filter((x) => x.id.length > 0);
  } catch {
    return [];
  }
}

function write(list: RecentJob[]) {
  if (!hasStorage()) return;
  try {
    localStorage.setItem(RECENT_JOBS_STORAGE_KEY, JSON.stringify(list));
  } catch (e) {
    // quota cheia ou storage bloqueado — só registra no console
    console.warn("recentJobs: falha ao gravar no localStorage:", e);
  }
  // dispara evento local (mesma aba)
  window.dispatchEvent(new CustomEvent(RECENT_JOBS_EVENT));
}

export function getRecent(): RecentJob[] {
  if (!hasStorage()) return [];
  try {
    const raw = localStorage.getItem(RECENT_JOBS_STORAGE_KEY);
    const list = safeParse(raw);
    // mais recentes primeiro
    return [...list].sort((a, b) => b.ts - a.ts);
  } catch {
    return [];
  }
}

export function pushRecent(idRaw: string) {
  if (!hasStorage()) return;
  const id = (idRaw ?? "").trim();
  if (!id) return;

  const now = Date.now();
  const list = getRecent();

  // remove duplicata e insere no topo
  const filtered = list.filter((x) => x.id !== id);
  filtered.unshift({ id, ts: now });

  write(filtered.slice(0, MAX_ITEMS));
}

export function removeRecent(idRaw: string) {
  if (!hasStorage()) return;
  const id = (idRaw ?? "").trim();
  const list = getRecent().filter((x) => x.id !== id);
  write(list);
}

export function clearRecent() {
  if (!hasStorage()) return;
  try {
    localStorage.removeItem(RECENT_JOBS_STORAGE_KEY);
  } finally {
    window.dispatchEvent(new CustomEvent(RECENT_JOBS_EVENT));
  }
}

/**
 * Assina atualizações (na aba atual + entre abas via 'storage').
 * Retorna um unsubscribe.
 */
export function onRecentJobsUpdated(handler: () => void) {
  const custom = () => handler();
  const storage = (e: StorageEvent) => {
    if (e.key === RECENT_JOBS_STORAGE_KEY) handler();
  };
  window.addEventListener(RECENT_JOBS_EVENT, custom as EventListener);
  window.addEventListener("storage", storage);

  return () => {
    window.removeEventListener(RECENT_JOBS_EVENT, custom as EventListener);
    window.removeEventListener("storage", storage);
  };
}
