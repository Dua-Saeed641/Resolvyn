# Resolvyn frontend

Next.js 14 (App Router) + Tailwind. Monochrome design system from `docs/project.md`.

* `/`  customer side: voice call or chat with the agent, live ticket, ticket history
* `/ops/*`  team console: overview, tickets (+ live detail workspace), agents, customers, knowledge (ingestion + rulebook by department),
  memory (knowledge graph), activity, human intelligence, learning signals, analytics, settings

Voice uses the browser's speech recognition (Chrome / Edge) and the backend's `/api/tts`. Real-time data comes from `/ws/ops` (`lib/live.tsx`)
and `/ws/call` (`lib/useCall.ts`). Components render state; decisions live in the backend.

```
npm install
npm run build && npm run start      # http://localhost:3000   (backend on :8000)
```
