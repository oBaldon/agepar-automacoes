// apps/portal/src/routes.tsx
import Home from "./pages/Home";
import ValidadorOrcamentoPage from "./pages/ValidadorOrcamento";
import JobResult from "./pages/JobResult";
import Arquivos from "./pages/Arquivos";

export const AppRoutes = [
  { path: "/", element: <Home /> },
  { path: "/validador-orcamento", element: <ValidadorOrcamentoPage /> },
  { path: "/jobs/:id", element: <JobResult /> },
  { path: "/arquivos", element: <Arquivos /> },
];
