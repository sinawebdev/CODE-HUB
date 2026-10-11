# KoforLink

Professional networking for Koforidua, Ghana. The original Apps Script demo has
been ported into a FastAPI modular monolith and a plain HTML/CSS/JavaScript frontend.
The frontend is served by FastAPI and calls `/api/v1` on the same origin.

## Layout

```text
koforlink/
  docker-compose.yml           local PostgreSQL
  frontend/
    index.html                 landing, auth and application shell
    css/main.css               demo styling
    js/                        ES modules and the HTTP client
  backend/
    requirements.txt
    .env.example
    alembic.ini
    migrations/                initial 42-table schema
    tests/                     isolated API behavior tests
    app/
      main.py                  FastAPI and static frontend
      cli.py                   setup, demo data and maintenance
      api/v1.py                module routers
      core/                    configuration, database, auth, email, events
      modules/                 feature services, schemas, models and routers
  tools/
    check_architecture.py      syntax, module boundaries and file sizes
    frontend-port/             frontend verification scripts
```

Implemented modules: platform, media, identity, profiles, network, companies,
opportunities, feed, stories, messaging, notifications, search, admin and analytics.
Messaging uses polling. Uploaded media is stored on local disk; private CVs and
documents require authorization or a signed link.

## Run on Windows (PowerShell)

Install Python 3.12+ and Docker Desktop, then from this folder:

```powershell
docker compose up -d
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `SECRET_KEY` in `backend/.env` to a random value. You can generate one with:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Create the schema, first administrator, and optional demo data:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.cli setup --admin-email you@example.com
.\.venv\Scripts\python.exe -m app.cli seed-demo
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open <http://localhost:8000> for the app and <http://localhost:8000/docs> for the API.
For the team-owned hosted database, follow [Supabase setup](docs/supabase.md).
Setup displays the first administrator's generated password once. Change it after
signing in. `seed-demo` is optional and skips data already seeded; demo member
`ama.mensah@demo.koforlink` uses `Demo@1234`.

On macOS/Linux use `python3 -m venv .venv` and `.venv/bin/python` in place of the
Windows virtual environment executable.

## Email, accounts and configuration

Registration requires email verification before member actions. In development,
email contents, including verification/reset codes, appear in the server logs.
Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `MAIL_FROM`
and `SMTP_USE_TLS` to send email. Password resets use a code and a new password.

Configuration comes from environment variables or `backend/.env`. Main options:

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection; defaults match Docker Compose |
| `MIGRATION_DATABASE_URL` | Optional direct/session connection for Alembic |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` | Connections per backend worker; defaults 5 / 0 |
| `SECRET_KEY` | JWT and signed media links |
| `ENVIRONMENT` | `development` by default; production requires a secret |
| `MEDIA_ROOT` | Uploaded files, defaults to `backend/media` |
| `PUBLIC_BASE_URL` | Optional absolute prefix for media links |
| `CORS_ORIGINS` | JSON list when the frontend uses a different origin |
| `STORY_EXPIRY_HOURS` | Defaults to 24 |

Access tokens are short-lived and refresh tokens rotate. The frontend stores
`kf_access` and `kf_refresh`, shares concurrent refresh requests, and signs out
when refresh fails. API successes use `{data, message}`; errors use
`{detail, code}` with an HTTP error status.

## Checks and operations

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe ..\tools\check_architecture.py
.\.venv\Scripts\python.exe -m app.cli maintenance
.\.venv\Scripts\python.exe -m app.cli list-admins
```

Tests default to isolated in-memory SQLite. To test PostgreSQL, set
`TEST_DATABASE_URL` to a **separate disposable local database ending in `_tests`** before running pytest;
the test fixture creates and drops its schema. Never use the app database for it.

The frontend verifier in `tools/frontend-port/verify.cjs` checks ES module imports,
the original demo call mapping, token refresh and headless Edge behavior. It uses
the local porting toolchain; see the script for its reference/tool paths.

For the concurrency regression, set `TEST_DATABASE_URL` to a disposable PostgreSQL
database ending in `_tests`, then run `python ../tools/check_concurrency.py` from
`backend/`. Final port verification is recorded in [docs/verification.md](docs/verification.md).

Architecture rules: modules call other modules' services and never import their
models. Services depend only on earlier modules in `app/modules/__init__.py`.
Cross-module reactions use `core/events.py`. Keep source files under 500 lines;
split cohesive service code into `service_<topic>.py` when needed.
