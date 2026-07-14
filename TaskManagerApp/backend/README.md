# Task Manager — Backend (FastAPI)

REST API for the Task Manager app. Python + FastAPI + SQLAlchemy 2.0 + JWT auth.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setup

```bash
cd backend
uv sync                       # create the venv and install dependencies
cp .env.example .env          # optional: customise settings (DB, secret, CORS)

uv run alembic upgrade head   # create the schema
uv run python -m app.seed     # load demo data (clears existing rows)
uv run uvicorn app.main:app --reload --port 8000
```

Interactive API docs are then at http://localhost:8000/docs. With no `.env`,
this uses a local SQLite file (`task_manager.db`).

### Using pip instead of uv

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

## Using PostgreSQL (via your local server / pgAdmin)

The schema and demo data are database-agnostic; point `DATABASE_URL` at Postgres
and run the same migration + seed commands.

1. **Create the database.** In pgAdmin, right-click **Databases → Create →
   Database…**, name it `task_manager`, save. (Or from a shell:
   `createdb -U postgres task_manager`.)
2. **Configure the connection.** In `backend/.env`, set (using the password you
   chose when installing PostgreSQL):
   ```
   DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/task_manager
   ```
3. **Create the schema and load data:**
   ```bash
   uv run alembic upgrade head
   uv run python -m app.seed
   ```

The tables and rows will then be visible in pgAdmin under
`task_manager → Schemas → public → Tables`.

## Migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/); the
app no longer creates tables at startup.

```bash
uv run alembic upgrade head                     # apply migrations
uv run alembic revision --autogenerate -m "…"   # after editing app/models.py
uv run alembic downgrade -1                      # roll back one revision
```

## Demo accounts

The seed script creates an org hierarchy. All accounts use the password
`password123`.

| Username | Name           | Manager |
| -------- | -------------- | ------- |
| alice    | Alice Anderson | — (admin) |
| bob      | Bob Brown      | alice   |
| carol    | Carol Clark    | alice   |
| dave     | Dave Davis     | bob     |

## API overview

| Method | Path                            | Description                          |
| ------ | ------------------------------- | ------------------------------------ |
| POST   | `/api/auth/register`            | Create an account, returns a token   |
| POST   | `/api/auth/login`               | Log in (form-encoded), returns token |
| GET    | `/api/auth/me`                  | Current user                         |
| GET    | `/api/users`                    | List users (for pickers)             |
| GET    | `/api/tasks`                    | Visible tasks (supports filters)     |
| POST   | `/api/tasks`                    | Create a task                        |
| GET    | `/api/tasks/{id}`               | Get one task                         |
| PATCH  | `/api/tasks/{id}`               | Update (edit-permission required)    |
| DELETE | `/api/tasks/{id}`               | Delete (edit-permission required)    |
| GET    | `/api/tasks/{id}/comments`      | List comments                        |
| POST   | `/api/tasks/{id}/comments`      | Add a comment                        |

`GET /api/tasks` query params: `sort` (`created`|`deadline`), `status`,
`created_by`, `assigned_to`, `managed` (`created`|`assigned`).

## Permission model (ported from the original py4web app)

- **Visibility**: a user sees tasks they created, tasks assigned to them, and
  tasks created by anyone below them in the org hierarchy (`manager_id`).
- **Edit / delete**: the task creator, anyone in the creator's management chain,
  or the admin (first-registered user).

## Notes on production

Tables are auto-created on startup for a zero-config demo. For a real
deployment, switch `DATABASE_URL` to Postgres and manage schema changes with
[Alembic](https://alembic.sqlalchemy.org/) instead of `create_all`, and set a
strong `SECRET_KEY`.
