import { Link } from "react-router-dom";
export default function Home(){
  return (
    <main className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Portal de Automações</h1>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <Link to="/validador-orcamento" className="block card transition">
          <h2 className="text-lg font-medium mb-2">Validador de Orçamento</h2>
          <p className="text-sm text-[var(--muted)]">Validar estrutura/preços (SINAPI/SUDECAP) e acompanhar jobs.</p>
        </Link>
      </div>
    </main>
  );
}
