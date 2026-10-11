#!/bin/sh
# Run on the free alwaysdata account after its private backend/.env is configured.
# This prepares the app; it does not switch the public site's configuration.
set -eu
umask 077
project_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root/backend"
test -f .env || { echo 'Configure private backend/.env before running this script.' >&2; exit 1; }
test -n "${ADMIN_EMAIL:-}" || { echo 'Set ADMIN_EMAIL to the owner email.' >&2; exit 1; }
chmod 600 .env
python -c 'import sys; assert sys.version_info >= (3, 12), "Select Python 3.12 or later in alwaysdata"'
if test ! -x .venv/bin/python; then python -m venv .venv; fi
.venv/bin/python -m pip install --no-cache-dir -r requirements.txt
.venv/bin/python -c 'from app.core.config import settings; assert settings.environment == "production"; assert settings.smtp_host, "Configure SMTP before release"'
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic check
.venv/bin/python "$project_root/tools/check_database.py"
# The setup command prints a first-admin password. Keep it off deployment logs.
if test ! -f .first-admin.txt; then
    .venv/bin/python -m app.cli setup --admin-email "$ADMIN_EMAIL" > .first-admin.txt
    chmod 600 .first-admin.txt
fi
printf '%s\n' 'App and database prepared. First-admin details are in private backend/.first-admin.txt.'
printf '%s\n' 'No demo accounts have been seeded. Switch the alwaysdata site to User program after readiness checks.'
