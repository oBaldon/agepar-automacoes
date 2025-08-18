import { useEffect, useState } from "react";
import { getJob, type JobOut } from "../lib/api";

export function useJobPolling(id?: string, intervalMs = 2000) {
  const [data, setData] = useState<JobOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let stop = false;

    async function tick() {
      try {
        const j = await getJob(id);
        if (!stop) setData(j);
        if (j.status === "finished" || j.status === "failed") return;
        setTimeout(tick, intervalMs);
      } catch (e: any) {
        if (!stop) setError(String(e?.message ?? e));
      }
    }

    tick();
    return () => { stop = true; };
  }, [id, intervalMs]);

  return { data, error };
}
