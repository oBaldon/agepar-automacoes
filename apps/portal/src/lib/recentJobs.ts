const KEY = 'agepar:recent-jobs';
const MAX = 12;

export type RecentJob = { id: string; createdAt: string };

export function getRecent(): RecentJob[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw) as RecentJob[];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

export function pushRecent(id: string) {
  const now = new Date().toISOString();
  let arr = getRecent().filter(j => j.id !== id);
  arr.unshift({ id, createdAt: now });
  if (arr.length > MAX) arr = arr.slice(0, MAX);
  localStorage.setItem(KEY, JSON.stringify(arr));
  window.dispatchEvent(new Event('recent-jobs-updated'));
}

export function clearRecent() {
  localStorage.removeItem(KEY);
  window.dispatchEvent(new Event('recent-jobs-updated'));
}
