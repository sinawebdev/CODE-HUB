"""Prepare alwaysdata over verified SSH without logging credentials.

The database must exist. The public site is switched separately after preparation.
Install paramiko in the local tool environment.
"""
import argparse
import base64
import hashlib
import json
import shlex
import sys
import time
from pathlib import Path, PurePosixPath

import paramiko


class VerifiedHostKey(paramiko.MissingHostKeyPolicy):
    def __init__(self, fingerprint):
        self.fingerprint = fingerprint

    def missing_host_key(self, client, hostname, key):
        actual = "SHA256:" + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
        if actual != self.fingerprint:
            raise RuntimeError(f"SSH server identity mismatch for {hostname}; no credentials were sent.")
        client.get_host_keys().add(hostname, key.get_name(), key)


def execute(client, command, secrets=(), payload=None, timeout=600):
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    if payload is not None:
        stdin.write(payload)
        stdin.flush()
    stdin.channel.shutdown_write()
    channel = stdout.channel
    started = time.monotonic()
    while True:
        for ready, read in ((channel.recv_ready, channel.recv), (channel.recv_stderr_ready, channel.recv_stderr)):
            if ready():
                output = read(65536).decode("utf-8", errors="replace")
                for secret in secrets:
                    if secret:
                        output = output.replace(secret, "[redacted]")
                print(output, end="", flush=True)
        if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
            break
        if time.monotonic() - started > timeout:
            channel.close()
            raise RuntimeError("Remote command timed out; inspect private server logs.")
        time.sleep(0.1)
    if channel.recv_exit_status():
        raise RuntimeError("Remote preparation failed; review the redacted output.")


CONFIGURE = r'''
import json, os, secrets, sys
from pathlib import Path
from urllib.parse import quote
plan = json.load(sys.stdin)
root = Path(plan['root'])
env = root / 'backend/.env'
if env.exists():
    print('Existing private backend/.env retained.')
    raise SystemExit(0)
password = quote(plan['database_password'], safe='')
url = 'postgresql+psycopg://' + quote(plan['database_user'], safe='') + ':' + password + '@' + plan['database_host'] + ':5432/' + plan['database'] + '?sslmode=require'
values = {
    'ENVIRONMENT':'production', 'DATABASE_URL':url, 'SECRET_KEY':secrets.token_urlsafe(48),
    'DATABASE_POOL_SIZE':'3', 'DATABASE_MAX_OVERFLOW':'0',
    'MEDIA_ROOT':str(root.parent / 'koforlink-media'), 'PUBLIC_BASE_URL':plan['public_base_url'],
    'SERVE_FRONTEND':'true', 'SMTP_HOST':plan['smtp_host'], 'SMTP_PORT':'587',
    'SMTP_USE_TLS':'true', 'MAIL_FROM':plan['mail_from']
}
def quoted(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('\n','\\n').replace('\r','\\r') + '"'
with os.fdopen(os.open(env, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as handle:
    handle.write(''.join(key + '=' + quoted(value) + '\n' for key,value in values.items()))
Path(values['MEDIA_ROOT']).mkdir(mode=0o700, exist_ok=True)
print('Private production configuration and persistent media directory created.')
'''

PROBE = r'''
import json, smtplib, ssl
from app.core.config import settings
from app.core.database_connection import make_database_engine
from sqlalchemy import text
engine=make_database_engine(settings.database_url)
with engine.connect() as connection:
    tables=connection.scalar(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name <> 'alembic_version'"))
engine.dispose()
assert tables == 42, 'Expected 42 application tables'
with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
    smtp.ehlo(); smtp.starttls(context=ssl.create_default_context()); smtp.ehlo()
    assert smtp.noop()[0] == 250
marker=settings.media_root / '.deployment-write-check'
marker.write_text('persistent storage check')
assert marker.read_text() == 'persistent storage check'
marker.unlink()
print(json.dumps({'application_tables':tables,'smtp_tls_connection':True,'media_writable':True,'email_delivery_tested':False}))
'''


def read_password(path):
    lines = [line for line in path.read_text(encoding="utf-8-sig").splitlines()
             if line and line != "PASTE_EXISTING_HOSTING_PASSWORD_HERE"]
    if len(lines) != 1:
        raise RuntimeError("The private password file must contain one password line.")
    return lines[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--database-password-file", type=Path)
    parser.add_argument("--admin-output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    password = read_password(args.password_file)
    database_password = read_password(args.database_password_file) if args.database_password_file else password
    root = PurePosixPath(plan["root"])
    if not root.is_absolute() or root.parent != PurePosixPath("/home") / plan["username"] or root.name != "koforlink":
        raise RuntimeError("The deployment directory must be /home/ACCOUNT/koforlink.")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(VerifiedHostKey(plan["fingerprint"]))
    try:
        client.connect(plan["host"], username=plan["username"], password=password,
                       look_for_keys=False, allow_agent=False, timeout=20, auth_timeout=20, banner_timeout=20)
        print("Authenticated to the verified hosting server.", flush=True)
        q = shlex.quote
        command = "\n".join([
            "set -eu", "umask 077",
            f"if test -d {q(str(root))}; then",
            f"  cd {q(str(root))}",
            f"  test \"$(git remote get-url origin)\" = {q(plan['repository'])}",
            '  test -z "$(git status --porcelain)"',
            f"  git fetch origin {q(plan['branch'])}",
            f"  git checkout {q(plan['branch'])}",
            f"  git merge --ff-only origin/{q(plan['branch'])}",
            "else",
            f"  git clone --single-branch --branch {q(plan['branch'])} {q(plan['repository'])} {q(str(root))}",
            f"  cd {q(str(root))}",
            "fi", "git rev-parse HEAD",
        ])
        execute(client, command, (password, database_password), timeout=180)
        payload = dict(plan, database_password=database_password)
        execute(client, "PYTHON_VERSION=3.12 python -c " + q(CONFIGURE),
                (password, database_password), json.dumps(payload))
        execute(client, f"cd {q(str(root))} && PYTHON_VERSION=3.12 ADMIN_EMAIL={q(plan['admin_email'])} sh deploy/alwaysdata-prepare.sh",
                (password, database_password))
        execute(client, f"cd {q(str(root / 'backend'))} && .venv/bin/python -c " + q(PROBE),
                (password, database_password), timeout=60)
        args.admin_output.parent.mkdir(parents=True, exist_ok=True)
        with client.open_sftp() as sftp:
            sftp.get(str(root / "backend/.first-admin.txt"), str(args.admin_output))
        print("Preparation passed. Private admin details saved locally; the public site still needs switching.")
    finally:
        client.close()


if __name__ == "__main__":
    try:
        main()
    except (paramiko.AuthenticationException, paramiko.SSHException, OSError, ValueError, RuntimeError) as error:
        if isinstance(error, paramiko.AuthenticationException):
            print("Hosting sign-in failed. Check the existing SSH password.", file=sys.stderr)
        elif isinstance(error, RuntimeError):
            print(str(error), file=sys.stderr)
        else:
            print(f"Preparation stopped ({type(error).__name__}); no secrets were printed.", file=sys.stderr)
        raise SystemExit(1)
