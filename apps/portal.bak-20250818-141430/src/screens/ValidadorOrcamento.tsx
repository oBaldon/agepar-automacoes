import { Page, Card, Input, Button } from "@agepar/ui";

export default function ValidadorOrcamento() {
  return (
    <Page title="Validador de Orçamento">
      <Card>
        <div className="grid gap-4">
          <Input label="Nome da Tarefa" placeholder="Ex.: Validação SUDECAP 2025-04" />
          <Input label="Arquivo" type="file" />
          <div><Button>Enviar</Button></div>
        </div>
      </Card>
    </Page>
  );
}
