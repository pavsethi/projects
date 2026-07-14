# Task Manager

A team task tracker with an org hierarchy: assign tasks, comment on them, filter
by owner/status/deadline, and see deadlines on a calendar. What you can see and
edit is scoped to your place in the reporting chain.

Originally built as a school project on [py4web](https://py4web.com/); this
repository is a modern rewrite of that app.

## Hosted App
https://projects-henna-pi.vercel.app/login

## Tech stack

| Layer      | Technology                                              |
| ---------- | ------------------------------------------------------- |
| Backend    | Python · FastAPI · SQLAlchemy 2.0 · Pydantic · JWT auth |
| Frontend   | React 18 · TypeScript · Vite · Tailwind CSS v4          |
| Database   | SQLite (dev) — swappable for Postgres via `DATABASE_URL`|

## Quick start

Two terminals. **Backend** ([details](backend/README.md)):

```bash
cd backend
uv sync
uv run alembic upgrade head        # create the schema
uv run python -m app.seed          # load demo data
uv run uvicorn app.main:app --reload --port 8000
```

> Uses SQLite by default. To run on your local PostgreSQL instead, set
> `DATABASE_URL` in `backend/.env` — see [backend/README.md](backend/README.md#using-postgresql-via-your-local-server--pgadmin).

**Frontend** ([details](frontend/README.md)):

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

Then open http://localhost:5173 and log in as **`bob`** / **`password123`**
(other demo accounts: `alice`, `carol`, `dave`).

## Features

- **Auth** — register / log in with JWT; pick your manager at signup to place
  yourself in the org tree.
- **Tasks** — title, description, deadline, status
  (pending / acknowledged / rejected / completed / failed), and an assignee.
- **Org-scoped visibility** — you see tasks you created, tasks assigned to you,
  and tasks created by anyone who reports to you (recursively).
- **Permissions** — you can edit/delete a task if you created it, you manage the
  creator, or you're the admin (first user). The UI hides Edit when you can't.
- **Comments** — threaded discussion on each task.
- **Filtering** — by status, creator, assignee, "managed users", or sorted by
  date created / deadline.
- **Calendar** — highlights days that have task deadlines.

## What changed from the original

The original py4web app packed models, controllers, and templated Vue-from-CDN
into a single framework. This rewrite splits it into a typed REST API and a
built SPA:

- **pydal DAL** → SQLAlchemy 2.0 ORM models with real relationships.
- **py4web `auth` + cookie sessions** → stateless JWT auth with hashed passwords.
- **Server-rendered YATL templates + global `app.config` Vue** → a component-based
  React + TypeScript SPA with a typed API client.
- **`.table` migration files** → SQLAlchemy models with Alembic migrations.
- **Bulma via CDN** → Tailwind CSS with a small design system.

The org-hierarchy visibility and edit-permission rules were ported faithfully;
see [`backend/app/permissions.py`](backend/app/permissions.py).

## Deployment

The app is deploy-ready: the backend ships a `Dockerfile` that runs migrations on
start, the frontend reads its API origin from `VITE_API_BASE_URL`, and managed
`postgres://` URLs are auto-normalized. See **[DEPLOY.md](DEPLOY.md)** for a
step-by-step Render (backend + Postgres) + Vercel (frontend) walkthrough.

## Repository layout

```
backend/     FastAPI application (app/ package, Alembic migrations, Dockerfile, seed script)
frontend/    React + Vite single-page app (vercel.json for SPA routing)
apps/        The original py4web project, kept for reference
DEPLOY.md    Render + Vercel deployment walkthrough
```

## Original version

The initial py4web implementation lives under [`apps/task_manager`](apps/task_manager)
and is left untouched for comparison.
To run this application, pull the code to a local folder.

Install py4web with: pip install py4web.

Once py4web is installed. Run: **py4web run apps**

Navigate to this link: http://127.0.0.1:8000/task_manager

