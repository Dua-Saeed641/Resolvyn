# Resolvyn frontend

Next.js (App Router, TypeScript, Tailwind) dashboard implementing the prototype UI spec in
[`../docs/project.md`](../docs/project.md), on top of the architecture in
[`../docs/architecture.md`](../docs/architecture.md). See [`../docs/claude.md`](../docs/claude.md)
for the design-system and vocabulary rules this codebase must follow.

## Run locally

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Requires the backend running at `http://localhost:8000` (see `../backend/README.md`).

## Layout

```
app/                 Routes — one folder per sidebar section (project.md §10)
components/
  layout/            Sidebar, TopBar, AppShell
  ui/                 Design-system primitives (StatusBadge, ConfidenceIndicator, MetricCard, ...)
  tickets/ agents/ customers/ knowledge/ tools/ activity/
  human-intelligence/ learning/   Domain components (project.md §83)
features/            Per-domain TypeScript types, mirroring backend/app/models
lib/                  constants.ts (shared vocabulary), api.ts (fetch client), utils.ts
```
