"""Operational commands (replaces the Apps Script demo's setupSystem, seedDemoData, resetAdminPassword,
listAllAdmins, dailyMaintenance and resetAllData).

Create the schema first with `alembic upgrade head`, then from the backend folder:

    python -m app.cli setup [--admin-email you@example.com]   default settings + first Super Admin
    python -m app.cli seed-demo                               demo people, company, jobs, posts, event
    python -m app.cli list-admins
    python -m app.cli reset-admin-password --email admin@koforlink.local
    python -m app.cli maintenance                             expire stories, purge old sessions/codes
    python -m app.cli reset-data --yes                        delete ALL rows (keeps the schema)
"""
import argparse
import os
import secrets
import sys

from app.core.config import settings
from app.core.database import Base, SessionLocal
from app.modules import load_models
from app.modules.identity import service as identity_service
from app.modules.identity import service_admin as users_admin
from app.modules.platform import service as platform_service
from app.modules.profiles import service as profiles_service

load_models()


def _password() -> str:
    return secrets.token_urlsafe(12)


def setup(args) -> None:
    settings.media_root.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        added = platform_service.ensure_defaults(db)
        print(f"Settings: {len(added)} default(s) added.")
        admins = users_admin.list_admins(db)
        if admins:
            print(f"Admin already exists: {admins[0].email}")
            return
        email = (args.admin_email or os.environ.get("ADMIN_EMAIL") or "admin@koforlink.local").lower()
        password = _password()
        user = users_admin.create_admin(db, email, password)
        profiles_service.create_profile(db, user)
        platform_service.audit(db, "", "CREATE_FIRST_ADMIN", "User", user.id, email)
        db.commit()
        print("=== FIRST ADMIN CREATED (shown once; sign in and change the password) ===")
        print(f"Email:    {email}\nPassword: {password}")


def seed_demo(_args) -> None:
    from app.demo_data import seed

    with SessionLocal() as db:
        result = seed(db)
    if result["skipped"]:
        print(f"Demo data already present ({result['demoUsers']} demo users). Nothing to do.")
    else:
        print(f"Demo data seeded: {result['demoUsers']} users. Sign in as e.g. ama.mensah@demo.koforlink "
              f"with password {result['password']}")


def list_admins(_args) -> None:
    with SessionLocal() as db:
        admins = users_admin.list_admins(db)
        if not admins:
            print("No admin users exist. Run: python -m app.cli setup")
        for user in admins:
            print(f"Role: {user.role} | Email: {user.email} | Status: {user.status} | Name: {user.full_name}")


def reset_admin_password(args) -> None:
    with SessionLocal() as db:
        user = identity_service.find_user_by_email(db, args.email)
        if user is None or user.role not in ("Super Admin", "Admin"):
            sys.exit(f"No admin with email {args.email}. Use list-admins to see admins.")
        password = args.password or _password()
        users_admin.reset_password(db, user, password)
        print(f"=== ADMIN PASSWORD RESET ===\nEmail:    {user.email}\nPassword: {password}")


def maintenance(_args) -> None:
    from app.modules.stories import service as stories_service

    with SessionLocal() as db:
        expired = stories_service.cleanup_expired_stories(db)
        purged = users_admin.purge_expired_sessions(db)
    print(f"Stories expired: {expired}. Old sessions/codes purged: {purged}.")


def reset_data(args) -> None:
    if not args.yes:
        sys.exit("This deletes every row in every table. Re-run with --yes to confirm.")
    with SessionLocal() as db:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    print("All KoforLink data cleared. Run `python -m app.cli setup` to restore defaults.")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="KoforLink operations")
    commands = parser.add_subparsers(dest="command", required=True)
    cmd = commands.add_parser("setup", help="default settings + first Super Admin")
    cmd.add_argument("--admin-email")
    cmd.set_defaults(run=setup)
    commands.add_parser("seed-demo", help="demo content for local development").set_defaults(run=seed_demo)
    commands.add_parser("list-admins").set_defaults(run=list_admins)
    cmd = commands.add_parser("reset-admin-password")
    cmd.add_argument("--email", required=True)
    cmd.add_argument("--password", help="defaults to a random password")
    cmd.set_defaults(run=reset_admin_password)
    commands.add_parser("maintenance", help="run daily").set_defaults(run=maintenance)
    cmd = commands.add_parser("reset-data", help="delete ALL rows")
    cmd.add_argument("--yes", action="store_true")
    cmd.set_defaults(run=reset_data)
    args = parser.parse_args(argv)
    args.run(args)


if __name__ == "__main__":
    main()
