import { Page, Card, Button } from "@agepar/ui";
import { Link } from "react-router-dom";

export default function Home() {
  return (
    <Page title="Portal de Automação">
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <Card>
          <h2 className="text-lg font-medium mb-2">Validador de Orçamento</h2>
          <p className="text-sm text-[var(--color-muted)] mb-4">
            Envie planilhas e valide informações de orçamento automaticamente.
          </p>
          <Link to="/auto-validador-orcamento">
            <Button>Abrir</Button>
          </Link>
        </Card>
      </div>
    </Page>
  );
}
