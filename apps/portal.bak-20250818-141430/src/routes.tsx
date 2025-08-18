import Home from "./pages/Home";
import ValidadorOrcamentoPage from "./pages/ValidadorOrcamento";
import JobResult from "./pages/JobResult";

export const AppRoutes = [
  { path: "/", element: <Home /> },
  { path: "/validador-orcamento", element: <ValidadorOrcamentoPage /> },
  { path: "/jobs/:id", element: <JobResult /> },
];
