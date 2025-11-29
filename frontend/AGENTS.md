# Repository Guidelines

## Project Structure & Modules
- Entry: `src/main.tsx` mounts `<App />`; routes live in `src/App.tsx`.
- UI: feature components in `src/components` with shared pieces in `components/ui` and `components/common`.
- Pages: route-level views in `src/pages`; keep them thin and delegate to components/hooks.
- State & logic: contexts in `src/context`, reusable hooks in `src/hooks`, helpers in `src/lib` and `src/utils`, shared contracts in `src/types`, data/mocks in `src/services`.
- Assets: static files in `public/`; build output in `dist/` (do not edit manually).

## Setup & Local Development
- Node 18+ with npm (lockfile present). Install once: `npm install`.
- Run dev server with hot reload: `npm run dev` (Vite, port printed in terminal).
- Production sanity check: `npm run build && npm run preview`.

## Build, Lint, and Checks
- `npm run build`: `tsc` type-checks then Vite bundles to `dist/`.
- `npm run lint`: ESLint on `.ts`/`.tsx`; fix before PRs.
- Pre-PR habit: `npm run lint && npm run build` to catch type or bundling errors early.

## Coding Style & Naming Conventions
- TypeScript + React function components; prefer hooks over classes.
- Files: components/pages in `PascalCase.tsx`; helpers/hooks in `camelCase.ts/tsx`.
- Styling: Tailwind utilities plus tokens in `src/index.css`; centralize shared UI in `components/ui` or `components/common` instead of duplicating class strings.
- State: colocate local state; share via contexts. Keep side effects in hooks or services, not in render bodies.
- Types: export shared shapes from `src/types`; type all props and service responses.

## Testing Guidelines
- No automated suite is wired yet. When adding one, prefer Vitest + React Testing Library; co-locate specs as `ComponentName.test.tsx` near the source or under `src/__tests__/`.
- For now, rely on `npm run lint` and `npm run build`; note manual QA steps in PRs.

## Commit & Pull Request Guidelines
- Commits: short, imperative (e.g., `Add timeline filters`, `Fix command palette keybind`); bundle related changes, avoid WIP noise.
- PRs: include summary, linked issues, screenshots for UI changes, and any config/env updates. Confirm `npm run lint` and `npm run build` pass.

## Security & Configuration
- Use Vite env vars prefixed with `VITE_`; keep secrets out of git and provide `.env.example` entries for new settings.
- Prefer mock data in `src/services` for demos; never commit keys or credentials.
