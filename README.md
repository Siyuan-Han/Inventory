# Wedding Dress Inventory

Track dress styles, factory orders, shipping status and sales. Two partners, one
shared Supabase database, mobile-first web UI.

- **Backend** — FastAPI + SQLAlchemy 2 (async) + asyncpg, talking to Postgres on Supabase
- **Frontend** — Vue 3 + Vite + Pinia + Tailwind CSS 4

```
backend/            FastAPI service
  main.py           app entry, /health, /statuses, /stats
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
pip install -r requirements.txt        # or: poetry install
cp .env.example .env                   # then fill in DATABASE_URL
```

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

`DATABASE_URL` must be URL-encoded — `!` becomes `%21`:

```
postgresql+asyncpg://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

The direct host resolves over IPv6 only. On an IPv4-only network use the session
pooler string from the Supabase dashboard instead:

```
postgresql+asyncpg://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

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

| Method | Path | |
| --- | --- | --- |
| GET | `/dresses?search=` | list with rollups |
| POST | `/dresses` | create |
| GET | `/dresses/{id}` | detail with orders and sales |
| PUT | `/dresses/{id}` | update |
| DELETE | `/dresses/{id}` | delete (cascades) |
| GET | `/orders?dress_id=&status=` | list |
| POST | `/orders` | create |
| GET/PUT/DELETE | `/orders/{id}` | read / update status / delete |
| GET | `/sales?dress_id=` | list |
| POST | `/sales` | create |
| PUT/DELETE | `/sales/{id}` | update / delete |
| GET | `/stats` | dashboard totals |
| GET | `/statuses` | the pipeline, for the UI |
| GET | `/health` | liveness |

## Tests

```bash
cd frontend && npm test
```

Mounts every view and component against a stubbed API and checks the store's
error handling.

## Not yet built

Photo upload to Supabase Storage (the dress form takes a URL for now),
authentication, realtime sync, deployment config.
