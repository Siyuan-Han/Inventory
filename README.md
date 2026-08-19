# Wedding Dress Inventory

Track dress styles, factory orders, shipping status and sales. Two partners, one
shared Supabase database, mobile-first web UI.

- **Backend** — FastAPI + SQLAlchemy 2 (async) + asyncpg, talking to Postgres on Supabase
- **Frontend** — Vue 3 + Vite + Pinia + Tailwind CSS 4

```
vercel.json         routes /api/* to the backend, everything else to the frontend
backend/            FastAPI service
  main.py           app entry, routes under /api: /health, /statuses, /stats
  config.py         settings from .env
  database.py       async engine + session
  models.py         dress, dress_order, sale
  schemas.py        Pydantic v2 models + the status pipeline
  rollups.py        derived per-dress numbers
  routers/          dresses.py, orders.py, sales.py
frontend/
  src/api.js        API client
  src/stores/       Pinia store
  src/views/        Dashboard, DressList, DressDetail, AddDress
  src/components/   DressCard, OrderForm, SaleForm
```

## Setup

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                   # then fill in DATABASE_URL
```

> There's no `pyproject.toml` here on purpose — Vercel's Python builder prefers
> one over `requirements.txt` when both exist, but a Poetry app-mode project
> (`package-mode = false`, needed since this isn't a distributable library)
> can't satisfy that builder's PEP 517 build step. `requirements.txt` is the
> single source of truth for both local installs and deployment.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

## Running

Terminal 1 — API on :8001

```bash
cd backend
source venv/bin/activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

Terminal 2 — UI on :5174

```bash
cd frontend
npm run dev
```

Open http://localhost:5174. Interactive API docs are at http://localhost:8001/docs.

The dev server also binds to your LAN address, so you can open the same URL on a
phone and "Add to Home Screen" to install it.

## Database

Tables are created on startup if they are missing (`Base.metadata.create_all`),
so a fresh Supabase project needs no manual SQL.

This project's direct host (`db.<project-ref>.supabase.co:5432`) refuses
connections even though the project is active — the session pooler is the one
that works, so `DATABASE_URL` uses it:

```
postgresql+asyncpg://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

The region isn't shown in the dashboard's default connection string — get it
from Settings → Database → Connection Pooling (this project is `us-east-2`).
The pooler username is `postgres.<project-ref>`, not plain `postgres`.

`DATABASE_URL` must be URL-encoded — `!` becomes `%21` (not needed for the
current password).

For offline work, point it at SQLite — no other change needed:

```
DATABASE_URL=sqlite+aiosqlite:///./dev.db
```

## Order pipeline

Orders move through five stages. Advancing an order stamps its timestamp and
backfills any earlier stage that was skipped, so the timeline stays readable.

`ordered → shipped_from_factory → arrived_shipping_center → arrived_us → received`

Stock is derived, not stored: `in_stock = quantity on received orders − sales`.

## API

All routes live under `/api` (see [Deployment](#deployment) for why).

| Method | Path | |
| --- | --- | --- |
| GET | `/api/dresses?search=&archived=&supplier=&not_received=` | list with rollups |
| POST | `/api/dresses` | create (server assigns the code if omitted) |
| GET | `/api/dresses/{id}` | detail with orders and sales |
| PUT | `/api/dresses/{id}` | update |
| POST | `/api/dresses/{id}/archive` \| `/restore` | archive / unarchive |
| DELETE | `/api/dresses/{id}` | delete (cascades) |
| GET | `/api/dresses/next-code` | preview the next auto-assigned code |
| GET | `/api/dresses/suppliers` | distinct supplier names, for a filter dropdown |
| GET | `/api/orders?dress_id=&status=` | list |
| POST | `/api/orders` | create |
| GET/PUT/DELETE | `/api/orders/{id}` | read / update status (`status_date` backdates it) / delete |
| GET | `/api/sales?dress_id=` | list |
| POST | `/api/sales` | create (`cash_amount` records a cash/card split) |
| PUT/DELETE | `/api/sales/{id}` | update / delete |
| GET | `/api/stats` | dashboard totals (all-time; financial figures include archived dresses) |
| GET | `/api/stats/monthly?month=YYYY-MM` | one month's revenue/cost/profit/cash-vs-card |
| GET | `/api/statuses` | the pipeline, for the UI |
| GET | `/api/health` | liveness |

## Tests

```bash
cd frontend && npm test
```

Mounts every view and component against a stubbed API and checks the store's
error handling.

## Deployment

Deployed as a single Vercel project using [Services](https://vercel.com/docs/services)
— the frontend and backend build separately but share one domain, routed by the
root [vercel.json](vercel.json):

- `/api/*` → the FastAPI backend service (`backend/`, entrypoint `main:app`)
- everything else → the Vue frontend service (`frontend/`, framework `vite`)

Backend routes live under `/api` in the FastAPI app itself (see `API_PREFIX` in
`backend/main.py`) specifically so this split works — the frontend's own
client-side routes (`/dresses/:id`, etc.) use the same path names, so without
the prefix the two would collide over who owns `/dresses`.

Because both services share one domain, the frontend calls the API with a
relative path (`api.js` defaults `VITE_API_BASE_URL` to `/api` when unset) —
no CORS, and nothing to configure for production. Local dev sets
`VITE_API_BASE_URL=http://localhost:8001/api` in `frontend/.env` instead,
since the two dev servers run on different ports.

### Environment variables (set in Vercel → Project Settings → Environment Variables)

Backend:
- `DATABASE_URL` — the Supabase **session pooler** string (see [Database](#database) above)
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_BUCKET`

Frontend:
- `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_SUPABASE_BUCKET` — for direct-to-Storage photo uploads
- `VITE_API_BASE_URL` — leave unset; it only needs a value for local dev

Nothing else to configure — connecting the GitHub repo and setting those
variables is enough for Vercel to build both services on every push to `main`.

## Not yet built

Authentication, realtime sync between the two partners' sessions.
