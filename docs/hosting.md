# KoforLink hosting and release status

Checked on 11 October 2026. The user requires strictly free hosting without idle cold starts. No paid hosting is authorized.

## GitHub and database

- UI commit: `b1b1977ea7c5e5ea1ac912a186ad863c0f18b985`, titled **Sina's UI/UX change**.
- Branch: [sinas-ui-ux-change](https://github.com/sinawebdev/CODE-HUB/tree/sinas-ui-ux-change).
- The local and remote UI commit IDs were compared and matched.
- Supabase access was verified for `sinawebdev's Org`. A new `koforlink` project in `eu-west-1` was quoted at $0/month, and creation was attempted after user confirmation.
- Supabase rejected creation because the account already owns/administers two active free projects. No new database was created. The user chose to leave creation pending; existing projects were not changed.
- No Render service was created. The user excluded Render because of idle cold starts.

## Hosting options

The app is a FastAPI server using SQLAlchemy/psycopg and PostgreSQL. FastAPI also serves the frontend from the same origin. Hosting only the HTML does not provide the app's API or database.

| Option | Idle behavior | Cost and practical fit |
| --- | --- | --- |
| alwaysdata Free | Site idle timeout can be set to `0` to disable inactivity stops. The provider still reserves the ability to stop applications. | Free without a card; 1 GB disk, 256 MB RAM, quarter CPU, personal-use plan, and an `alwaysdata.net` website address. Supports ASGI/Uvicorn. Best candidate for a free preview without card verification, subject to a real resource/runtime check. |
| Oracle Always Free VM | A running VM serves requests continuously; Oracle can reclaim idle free VMs under its seven-day utilization rules. | Best free candidate for the current Python server. Requires account/card verification, available regional capacity and server administration. Free resources must be provisioned in the account's home region. |
| Google Compute Engine free-tier VM | A running non-preemptible VM avoids request-driven startup. | Includes an eligible US-region e2-micro VM and limited disk/egress. Requires billing; network/IP charges and overages need separate review. Not certified as a $0 complete deployment. |
| Railway | Optional Serverless mode sleeps services; keep it disabled for continuous operation. | Free plan provides only $1/month of resource credit. Continuous Python operation may exceed that allowance. Hobby starts at $5/month and includes $5 usage; excess usage costs extra. |
| Koyeb Free | Sleeps after one hour without traffic; cannot disable this behavior on Free. | Does not meet the user's no-idle-sleep requirement. |
| Render Free | Sleeps after 15 minutes without traffic. | Excluded by the user. |
| Cloudflare Pages / Python Workers | Pages can serve static files; Python Workers use the WebAssembly Python runtime. | Pages alone cannot run this backend. Moving this app to Workers would require a separately verified database-driver, runtime and media-storage adaptation. That conversion has not been implemented. |

alwaysdata and Oracle are candidates, not deployed services or uptime guarantees. No matching alwaysdata or Oracle compute connector was found by plugin discovery. The larger VM preparation below is an optional route if Oracle is selected; it does not require a paid VM.

Sources: [Oracle Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), [Oracle signup requirements](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm), [Google Cloud free tier](https://docs.cloud.google.com/free/docs/free-cloud-features), [Railway pricing](https://docs.railway.com/pricing/plans), [Railway Serverless](https://docs.railway.com/deployments/serverless), [Koyeb scale-to-zero](https://www.koyeb.com/docs/run-and-scale/scale-to-zero), [Render Free](https://render.com/docs/free), [Cloudflare Python packages](https://developers.cloudflare.com/workers/languages/python/packages/), [Supabase pricing](https://supabase.com/pricing).

## First free candidate: alwaysdata

The [Free offer](https://www.alwaysdata.com/en/offers/) provides 1 GB disk, 256 MB RAM and 0.25 CPU for personal use. [Signup does not require a credit card](https://www.alwaysdata.com/en/). Free websites use the supplied `alwaysdata.net` address; a custom website domain requires a different plan. This is a preview candidate: personal-use eligibility and actual memory use must be checked before broader release.

The provider supports [ASGI via a User program site](https://help.alwaysdata.com/en/docs/web-hosting/languages/python/configuration/). [Set the site's idle timeout to `0`](https://help.alwaysdata.com/en/docs/web-hosting/sites/misc/) to prevent the configured idle shutdown. This does not guarantee the provider never restarts the app; its separately managed 24/7 background Services feature is paid and is not part of this proposal.

After selecting Free and creating an account, deploy the full branch using SSH/SFTP and select Python 3.12 or later in the hosting panel. In the uploaded repository's `backend` directory:

```sh
python -m venv .venv
.venv/bin/python -m pip install --no-cache-dir -r requirements.txt
```

Configure a private `backend/.env` with the real database, random signing secret, `ENVIRONMENT=production`, `PUBLIC_BASE_URL=https://ACCOUNT.alwaysdata.net`, a persistent absolute `MEDIA_ROOT`, and working SMTP settings. The provider documents [SMTP on port 587 with STARTTLS](https://help.alwaysdata.com/en/docs/emails/use-an-email-address/), which fits this app. It also documents that SMTP authentication is unnecessary for a service running on its own servers. Use the account's actual sender address; verify delivery before claiming email works. Supabase remains pending.

Run Alembic and the read-only database check using the commands in [supabase.md](supabase.md), then create the first administrator. In Web > Sites, configure:

- Type: **User program**.
- Working directory: `/home/ACCOUNT/koforlink/backend`.
- Command: `/home/ACCOUNT/koforlink/backend/.venv/bin/python -m uvicorn app.main:app --host $IP --port $PORT`.
- Environment: `ENVIRONMENT=production` and `SERVE_FRONTEND=true`.
- Advanced idle timeout: **0**.
- Website address: the account's free `alwaysdata.net` address.

The provider supplies `$IP` and `$PORT`. Verify resource use, assets, database-backed sign-in and writes, upload persistence, email delivery, and response after inactivity before accepting this deployment.

### Current account preparation, 11 October 2026

The existing **koforlink** account was verified on **Free** (1 GB disk, 256 MB RAM, 0.25 CPU). The existing site is `koforlink.alwaysdata.net` and still runs its default PHP configuration.

The empty PostgreSQL 17 database **koforlink_app** has been created at `postgresql-koforlink.alwaysdata.net`, with the existing `koforlink` database user. Its 42 application tables have **not** yet been migrated. The existing SSH user is `koforlink` at `ssh-koforlink.alwaysdata.net`. The existing sender address is `koforlink@alwaysdata.net`.

`deploy/alwaysdata-prepare.sh` installs the server, checks production configuration, runs migrations/readiness, and creates the first administrator without seeding public demo accounts. Initial administrator details go to private, Git-ignored `backend/.first-admin.txt`, not deployment output.

`deploy/publish_alwaysdata.py` performs preparation through SSH. It requires a fingerprint read from the authenticated hosting panel, checks that identity before sending credentials, retains existing private configuration, and refuses to discard server source changes. The local plan, password input, dependency folder and downloaded administrator details belong in the Git-ignored `.validation` folder. They must never be committed. A separate database password can be supplied if it differs from the existing hosting password.

SSH preparation checks database schema/revision, media writability and SMTP TLS connectivity. It does **not** send email or switch the public site. Actual email delivery, public-site switching, idle behavior and hosted-browser acceptance remain pending. The existing SSH password is needed before source upload and migration can proceed.

## Prepared deployment for a continuously running Linux VM

`deploy/Dockerfile` packages both FastAPI and the complete frontend. It runs as an unprivileged user and stores uploaded files under `/var/lib/koforlink/media`. `deploy/compose.yaml` retains that directory in a named volume and restarts the app after process/VM restarts. Caddy terminates HTTPS and forwards the same-origin site/API to FastAPI. The API port is not published to the internet.

These files are prepared source. Docker was unavailable locally, so an image build, container startup, certificate issuance and VM/browser acceptance remain pending.

Before deployment, obtain a VM, a domain pointing to its public IP, the database connection, and an email sender. Configure the VM's firewall/security rules for 80/443, restrict SSH to the administrator, and install Docker with Compose using [Docker's official instructions](https://docs.docker.com/engine/install/ubuntu/).

On the VM, clone this branch and create `backend/.env` from `backend/.env.example`. Set a long random `SECRET_KEY`, the exact Supabase Session pooler `DATABASE_URL` on port 5432 with SSL, `PUBLIC_BASE_URL=https://YOUR_DOMAIN`, and working SMTP settings. Store credentials privately and never commit `.env`. Free Supabase can pause after inactivity, so avoiding web-server sleep alone does not guarantee an always-available database.

Run from the repository root after replacing the domain and admin email:

```sh
export SITE_ADDRESS=YOUR_DOMAIN
docker compose -f deploy/compose.yaml config --quiet
docker compose -f deploy/compose.yaml build
docker compose -f deploy/compose.yaml run --rm app python -m alembic upgrade head
docker compose -f deploy/compose.yaml run --rm app python -m alembic check
docker compose -f deploy/compose.yaml run --rm app python /app/tools/check_database.py
docker compose -f deploy/compose.yaml run --rm app python -m app.cli setup --admin-email YOUR_ADMIN_EMAIL
docker compose -f deploy/compose.yaml up -d
```

The administrator setup prints a generated password once; retain it privately. Do not seed public demo passwords on the public deployment. Check real registration/email delivery, sign-in, a feed write/read, private CV access, and an upload surviving `docker compose -f deploy/compose.yaml restart app`. `/health` proves only process availability; use `check_database.py` for database readiness.

Back up both PostgreSQL and the media volume. Removing volumes with `down -v` deletes saved media/certificate state. VM deployment, cloud database readiness, real email delivery, and public-browser verification are still pending.
