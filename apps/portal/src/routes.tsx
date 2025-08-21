// apps/portal/src/routes.tsx
import Home from "./pages/Home";
import ValidadorOrcamentoPage from "./pages/ValidadorOrcamento";
import Resultado from "./pages/Resultado";

export const AppRoutes = [
  { path: "/", element: <Home /> },
  { path: "/validador-orcamento", element: <ValidadorOrcamentoPage /> },
  { path: "/resultado", element: <Resultado /> },
];
