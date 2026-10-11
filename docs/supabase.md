# Supabase database setup

Status: connection support and table protection are prepared locally. A team-owned
Supabase project has not been connected or verified yet.

The request path is browser â†’ FastAPI â†’ Supabase PostgreSQL. FastAPI keeps the
existing accounts, login, permissions and API routes. Supabase provides the database.
Email still requires SMTP and uploaded files still use the backend's local disk.

## Team ownership

The agreed owner is another teammate. That person should create a separate
KoforLink organization and project, then invite your Supabase account to that
organization. Organization membership keeps access separate from personal projects.
Choose a region close to the eventual FastAPI host. Pricing and project limits
depend on the owner's account and selected plan.

When creating this project, keep automatic Data API table exposure off. In the
project's Data API integration settings, turn **Enable Data API** off. This app
uses its own FastAPI routes. The database migration also enables RLS and revokes
Data API role access to the 42 application tables and Alembic version table.
FastAPI connects as the table owner (`postgres` for initial setup), which can
access the tables while browser Data API roles cannot. RLS has no browser policies
because the current app authenticates users through FastAPI, not Supabase Auth.

## Connect FastAPI

In the project's **Connect** dialog, copy the exact **Session pooler** connection
string (port 5432). It supports IPv4 and suits the current persistent FastAPI app.
Copy the actual hostname; it cannot be guessed from the region.

From the project folder, install the backend dependencies as described in README,
then create `backend/.env` from `.env.example`. Put the real connection URL there:

```dotenv
DATABASE_URL=postgresql://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
MIGRATION_DATABASE_URL=
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=0
SECRET_KEY=YOUR_RANDOM_SECRET
```

Replace the placeholders. Percent-encode special characters in the database
password. Standard `postgresql://` URLs automatically use the installed psycopg 3
driver. Supabase connections default to encrypted SSL and reject plaintext fallback.
For certificate verification, download the project's CA certificate and use
`sslmode=verify-full&sslrootcert=PATH_TO_CERTIFICATE`.

Keep the real URL and password in `.env` or the deployment's secret settings. They
must not go into frontend JavaScript, chat, screenshots or Git. No Supabase API key
is needed for this direct database connection.

If the runtime later uses transaction pooling (port 6543), prepared statements
are disabled automatically. Set `MIGRATION_DATABASE_URL` to a direct or session
connection on port 5432; Alembic rejects the transaction pooler.
The pool limit applies per worker, so size workers against the project's connection
budget. Start with one FastAPI worker.

## Create and verify the schema

Use a new, empty KoforLink project. From `backend/` with its virtual environment:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe ..\tools\check_database.py
.\.venv\Scripts\python.exe -m app.cli setup --admin-email YOUR_ADMIN_EMAIL
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

`check_database.py` makes read-only queries. It checks connectivity, all application
tables, migration revision, RLS, backend ownership and Data API grants without
printing credentials. `/health` only reports that the server is running; it does
not prove the database is connected.

Open <http://localhost:8000>, sign in as the administrator, and verify profile/feed
writes and a fresh read after restarting FastAPI. Then test registration/email
verification, messaging, jobs and other member flows against this project. This
live verification is still pending until team project access and credentials exist.

`seed-demo` is optional for a development project. It creates demo accounts with a
publicly documented password, so do not run it on production.

Pytest creates and drops tables. Run it against SQLite or a separate disposable
local PostgreSQL database ending in `_tests`. The fixture rejects hosted Supabase
URLs. Never aim it at the KoforLink project.

Future PostgreSQL migrations must protect any new app tables in the same transaction.
Downgrading the protection migration retains its restrictions; downgrading the
initial schema drops the tables. It never restores public access automatically.

Sources: [Database connections](https://supabase.com/docs/guides/database/connecting-to-postgres),
[Data API security](https://supabase.com/docs/guides/api/securing-your-api),
[Organization access](https://supabase.com/docs/guides/platform/access-control).

## Local verification â€” 9 October 2026

- 104 tests passed on SQLite; 104 passed on an isolated local PostgreSQL database.
- Alembic model-drift check passed, plus upgrade â†’ downgrade â†’ upgrade.
- Database readiness check passed: 42 app tables and protected migration metadata.
- Real FastAPI sessions passed registration, email verification, profile access,
  post creation and persistence through a fresh database connection.
- Transactional simulation of Supabase's three Data API roles confirmed anonymous
  reads returned no rows and the migration revoked their table grants, including
  the bypass-RLS service role. All temporary role changes were rolled back.
- Architecture and whitespace checks passed. The existing Starlette/httpx warning remains.

These results verify the local preparation. They do not verify a hosted Supabase
connection, delivery of real email, cloud media storage, or a deployed backend.
