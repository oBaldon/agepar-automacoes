# agepar-automacoes

Monorepo com:
- `/apps/portal` — front único (React/Vite/TS)
- `/apps/validador-orcamento/api` — API da automação Validador de Orçamento
- `/apps/validador-orcamento/worker` — Worker/background da automação
- `/packages/tokens` — design tokens (CSS vars/Tailwind)
- `/packages/ui` — biblioteca de componentes compartilhada
- `/infra/nginx` — gateway (reverse proxy, headers)
- `docker-compose.yml` — orquestração local

## Dev rápido
- Dia 1: estrutura + import com histórico (git subtree).
- Próximos dias: tokens/UI, portal, dockerização, gateway, CI/CD.
