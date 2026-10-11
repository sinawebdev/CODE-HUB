"""Read-only database readiness check. Run from backend: python ../tools/check_database.py."""
import json
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def check() -> dict:
    from app.core.config import settings
    from app.core.database import Base
    from app.core.database_connection import make_database_engine
    from app.modules import load_models

    load_models()
    names = sorted(Base.metadata.tables)
    expected = ScriptDirectory.from_config(Config(str(ROOT / "backend/alembic.ini"))).get_current_head()
    engine = make_database_engine(settings.database_url)
    try:
        return inspect_database(engine, names, expected)
    finally:
        engine.dispose()


def inspect_database(engine, names: list[str], expected: str) -> dict:
    from app.core.database_connection import is_supabase

    with engine.connect() as connection:
        connection.scalar(text("SELECT 1"))
        actual = set(inspect(connection).get_table_names())
        missing = sorted(set(names + ["alembic_version"]) - actual)
        result = {"connected": True, "supabase": is_supabase(engine.url), "missing_tables": missing}
        if missing:
            result["ready"] = False
            return result
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
        result.update(revision=revision, expected_revision=expected, ready=revision == expected)
        if connection.dialect.name == "postgresql":
            rows = connection.execute(text("""
                SELECT c.relname, c.relrowsecurity,
                       r.rolbypassrls OR pg_has_role(current_user, c.relowner, 'USAGE') AS backend_access,
                       EXISTS (SELECT 1 FROM aclexplode(c.relacl) a WHERE a.grantee = 0) AS public_grant
                FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_roles r ON r.rolname = current_user
                WHERE n.nspname = 'public' AND c.relname = ANY(:tables)
            """), {"tables": names + ["alembic_version"]}).mappings().all()
            unsafe = [row["relname"] for row in rows if not row["relrowsecurity"] or row["public_grant"]]
            denied = [row["relname"] for row in rows if not row["backend_access"]]
            grants = connection.execute(text("""
                SELECT r.rolname, c.relname FROM pg_roles r CROSS JOIN pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE r.rolname IN ('anon', 'authenticated', 'service_role')
                  AND n.nspname = 'public' AND c.relname = ANY(:tables)
                  AND has_table_privilege(r.oid, c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
            """), {"tables": names + ["alembic_version"]}).all()
            result.update(unprotected_tables=unsafe, backend_access_denied=denied,
                          data_api_grants=[f"{role}:{table}" for role, table in grants])
            result["ready"] = result["ready"] and not (unsafe or denied or grants)
        return result


if __name__ == "__main__":
    try:
        result = check()
    except Exception as error:
        # Driver errors can contain passwords/connection strings. Never print them.
        print(json.dumps({"ready": False, "error_type": type(error).__name__,
                          "message": "Check database credentials, network access and migrations."}))
        raise SystemExit(1)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ready"] else 1)
