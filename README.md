# agepar-automacoes

Monorepo com:

- `/apps/portal` — front único (React/Vite/TS)
- `/apps/auto-<nome>/api` — backend por automação
- `/apps/auto-<nome>/worker` — worker/cron da automação (se houver)
- `/packages/tokens` — design tokens (CSS vars/Tailwind)
- `/packages/ui` — biblioteca de componentes compartilhada
- `/infra/nginx` — configs do gateway (reverse proxy, headers)
- `docker-compose.yml` — orquestração local

## Como começar

- Dia 1: estrutura + import da automação existente (com histórico).
- Próximos dias: tokens/UI, portal, dockerização, gateway, CI/CD.
