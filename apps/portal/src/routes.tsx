import { createRoutesFromElements, Route } from "react-router-dom";
import Home from "./screens/Home";
import ValidadorOrcamento from "./screens/ValidadorOrcamento";

export const AppRoutes = createRoutesFromElements(
  <>
    <Route path="/" element={<Home />} />
    <Route path="/auto-validador-orcamento" element={<ValidadorOrcamento />} />
  </>
);
