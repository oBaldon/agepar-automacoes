import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { JobsStorage, type StoredJob } from "../lib/jobsStore";

export default function JobQueue() {
  const [jobs, setJobs] = useState<StoredJob[]>(() => JobsStorage.all());

  useEffect(() => {
    const onStorage = () => setJobs(JobsStorage.all());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return (
    <section className="mt-6">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-semibold">Fila (local)</h2>
        {jobs.length > 0 && (
          <button
            className="text-sm text-blue-500 hover:underline"
            onClick={() => { JobsStorage.clear(); setJobs([]); }}
          >
            Limpar
          </button>
        )}
      </div>
      {jobs.length === 0 ? (
        <p className="text-sm text-gray-500">Sem envios ainda.</p>
      ) : (
        <ul className="space-y-2">
          {jobs.map(j => (
            <li key={j.id} className="border rounded-lg p-3 flex items-center justify-between">
              <div className="min-w-0">
                <div className="text-sm font-medium truncate">{j.label || j.op}</div>
                <div className="text-xs text-gray-500">{new Date(j.createdAt).toLocaleString()}</div>
              </div>
              <Link to={`/jobs/${j.id}`} className="text-blue-600 hover:underline text-sm">Abrir</Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
