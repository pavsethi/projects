# Deployment guide

This deploys the two pieces separately:

- **Backend** (FastAPI + Postgres) → [Render](https://render.com)
- **Frontend** (static React build) → [Vercel](https://vercel.com)

Both have free tiers and provide HTTPS automatically. The same repo works with
Railway, Fly.io, or Netlify with minor tweaks (notes at the end).

The repo is already deploy-ready: the backend has a `Dockerfile` that runs
migrations on start, the frontend reads its API URL from `VITE_API_BASE_URL`,
and `postgres://` connection strings are auto-normalized to the psycopg driver.

---

## 0. Prerequisites

1. Push this repo to GitHub (or GitLab/Bitbucket).
2. Generate a strong secret key for JWT signing — you'll paste it in step 1:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

---

## 1. Backend + database on Render

### 1a. Create the Postgres database

1. Render dashboard → **New → Postgres**.
2. Name it (e.g. `task-manager-db`), pick the free plan, **Create Database**.
3. When it's ready, copy the **Internal Database URL** (starts with
   `postgres://…`). You'll use it in the next step.

### 1b. Create the web service

1. **New → Web Service** → connect your repo.
2. Settings:
   - **Root Directory:** `backend`
   - **Runtime:** Docker (Render auto-detects the `Dockerfile`)
   - **Instance Type:** Free
3. Add **Environment Variables**:

   | Key                           | Value                                                        |
   | ----------------------------- | ----------------------------------------------------------- |
   | `DATABASE_URL`                | the Internal Database URL from step 1a                      |
   | `SECRET_KEY`                  | the key you generated in step 0                             |
   | `CORS_ORIGINS`                | `["https://REPLACE-AFTER-STEP-2.vercel.app"]` (fix in step 3) |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` (optional)                                             |

4. **Create Web Service.** On deploy, the container runs
   `alembic upgrade head` (creating the schema) and then starts uvicorn.
5. When it's live, note the backend URL, e.g. `https://task-manager-api.onrender.com`.
   Check `https://<backend-url>/api/health` returns `{"status":"ok"}`.

> **Migrations** run automatically on every start via the Docker `CMD`
> (`alembic upgrade head` is idempotent). For zero-downtime setups you can move
> it to a Render **Pre-Deploy Command** instead and drop it from the `CMD`.

---

## 2. Frontend on Vercel

1. Vercel dashboard → **Add New → Project** → import your repo.
2. Settings:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite (auto-detected; build `npm run build`, output `dist`)
3. Add an **Environment Variable**:

   | Key                  | Value                                          |
   | -------------------- | ---------------------------------------------- |
   | `VITE_API_BASE_URL`  | your backend URL from step 1 (no trailing `/`) |

4. **Deploy.** Note the frontend URL, e.g. `https://task-manager.vercel.app`.
   The included `vercel.json` handles SPA routing so deep links don't 404.

> `VITE_API_BASE_URL` is baked in at **build time**. If you change it later,
> trigger a redeploy so the new value takes effect.

---

## 3. Connect the two (CORS)

The browser will block API calls until the backend trusts the frontend's origin.

1. Back in Render → your web service → **Environment**.
2. Set `CORS_ORIGINS` to your real Vercel URL as a JSON array:
   ```
   ["https://task-manager.vercel.app"]
   ```
   (Add your custom domain too if you have one:
   `["https://task-manager.vercel.app","https://tasks.mydomain.com"]`.)
3. Save — Render redeploys automatically.

---

## 4. Create the first user

There's no seeded data in production. Open the frontend, go to **Sign up**, and
register **without selecting a manager** — the first user becomes the admin (can
edit any task), exactly as in the local demo.

> Want the demo dataset (alice/bob/carol/dave) in production instead? Open a
> shell on the Render service and run `uv run python -m app.seed`. This **wipes
> existing rows**, so only do it on a throwaway/demo database.

---

## Deploy checklist

- [ ] Repo pushed to GitHub
- [ ] Render Postgres created, Internal URL copied
- [ ] Render web service: root `backend`, Docker, `DATABASE_URL` + `SECRET_KEY` set
- [ ] `/api/health` returns ok
- [ ] Vercel project: root `frontend`, `VITE_API_BASE_URL` set to backend URL
- [ ] Backend `CORS_ORIGINS` updated to the Vercel URL, redeployed
- [ ] Registered the first (admin) user and logged in

---

## Alternatives

- **Railway / Fly.io** (backend): both build the `backend/Dockerfile` directly.
  Provision a Postgres add-on and set the same env vars. Fly injects `$PORT`,
  which the `CMD` already respects.
- **Netlify / Cloudflare Pages** (frontend): base directory `frontend`, build
  `npm run build`, publish `dist`. The included `public/_redirects` provides the
  SPA fallback (equivalent to `vercel.json`).
- **Single host**: you can also serve the built `frontend/dist` behind the same
  domain as the API (e.g. via a reverse proxy or FastAPI `StaticFiles`), which
  makes it same-origin and lets you drop `VITE_API_BASE_URL` and the CORS config
  entirely. Left out here to keep the two concerns independently deployable.

## Production hardening (optional, not required to ship)

- Rotate `SECRET_KEY` out of any shared history; never commit `.env`.
- Consider moving the JWT from `localStorage` to an httpOnly cookie to reduce
  XSS token-theft risk.
- Add rate limiting on `/api/auth/login`.
- Add a CI workflow (typecheck + build + `alembic upgrade` against a scratch DB)
  before deploys.
