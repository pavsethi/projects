# Task Manager — Frontend (React + Vite)

Single-page app for the Task Manager. React 18 + TypeScript + Vite + Tailwind CSS v4.

## Requirements

- Node 18+ (tested on Node 20)
- The backend running on http://localhost:8000 (the dev server proxies `/api`)

## Setup

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Other scripts:

```bash
npm run build      # type-check + production build to dist/
npm run preview    # serve the production build
npm run typecheck  # type-check only
```

## Structure

```
src/
  api/client.ts        Axios instance, token storage, error helper
  auth/AuthContext.tsx  Auth state (login/register/logout), JWT persistence
  components/           Layout, TaskCard, FilterBar, DeadlineCalendar, StatusBadge
  pages/                Login, Register, Dashboard, TaskForm (create/edit)
  types.ts              Shared TypeScript types (User, Task, Comment, filters)
```

The Vite dev server proxies API calls to the backend, so no CORS config or
`.env` is needed for local development (see `vite.config.ts`).
