# Security Intelligence Platform — Presentation Deck

## Slide 1 — Mission & Value
- Provide AI-first threat intelligence: ingest articles, chat over them, surface timelines, graphs, and predictions in one UI.
- Tailor responses by persona and industry via saved preferences and onboarding.
- Speed up analysts: live feed, visual context, and fast “explain it to…” translations for executives and builders.

## Slide 2 — Product Walkthrough (Demo Path)
- Start `npm install && npm run dev`; open the Vite URL.
- Onboarding captures role/industry; theme toggle in the header.
- Home: live feed sidebar, chat center, tabbed visualization pane (timeline, knowledge graph, predictions).
- Articles: filter by search/category/date; open details to see full content, graph, timeline, 48h forecast, Threat DNA, and infographics.
- From any article, “Ask AI about this” deep-links back to chat with a prefilled prompt.

## Slide 3 — Key Features
- Conversational analyst: `/api/chat` powers Q&A with follow-ups, timeline, graph data, and predictions.
- Visual intelligence: interactive knowledge graph, story timelines, and prediction cards tuned by confidence/urgency.
- Automation: generate infographics per article (summary, timeline, graph) with caching.
- Persona-aware summaries: “Explain to” service rewrites content for CEO/Board/Developers.
- Live feed: continuously refreshed headline cards; clicking seeds chat suggestions.

## Slide 4 — Architecture (Frontend)
- Stack: React + TypeScript + Vite; styling via Tailwind and Radix primitives; icons by Lucide.
- Routing in `src/App.tsx` with pages in `src/pages`; feature components under `src/components`.
- State: lightweight React state + `PreferencesContext` for persona/theme persistence (localStorage).
- API layer in `src/services` wraps REST endpoints (`/api/chat`, `/articles`, `/forecast/:id`, `/dna/:id`, `/graph/stats`, `/explain-to`, `/infographics`).
- Hooks (`useApi`, `useArticles`, `useArticle`) encapsulate fetching, loading/error states, and simple debouncing.

## Slide 5 — Data & Types
- Strong typing in `src/types`: articles, timelines, graphs, predictions, forecasts, DNA matches, infographics, and conversation responses.
- Graph model: nodes (articles, vulnerabilities, actors, techniques) + weighted edges; stats shown in the header.
- Forecast model: 48h hourly entries with risk levels and milestones; DNA model links historical precedents with similarity scores.

## Slide 6 — UX Details
- Command palette (⌘/Ctrl + K) for navigation and quick actions.
- Theme toggle and preference reset in header; onboarding gate ensures context-aware summaries.
- Loading/error components (`PageLoader`, `PageError`) keep flows resilient; responsive grid for dashboards.

## Slide 7 — Integration Notes
- Backend expects REST JSON; API base `/api` configurable via Vite proxy/server.
- Env vars should use `VITE_` prefix; secrets must stay out of the repo.
- For demos without backend, stub endpoints or mock `fetch` to return typed shapes from `src/types`.

## Slide 8 — Roadmap Suggestions
- Add Vitest + React Testing Library coverage for chat flows, services, and visual components.
- Add analytics for feature usage (chat vs. articles) and performance metrics around API latency.
- Expand explain-to personas and add RBAC for team sharing of insights and saved views.
